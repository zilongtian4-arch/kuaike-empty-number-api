// 快客检测 空号检测 API 示例（Go 1.18+，只用标准库）
// 用法：
//
//	export KUAIKE_API_KEY=您的密钥
//	go run main.go balance
//	go run main.go realtime 13800138000
//	go run main.go empty numbers.txt      # 空号检测（每行一个号码，至少 2000 个）
//
// 接口文档：https://kuaikejiance.com/api-docs
package main

import (
	"bufio"
	"bytes"
	"crypto/rand"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"net/http"
	"os"
	"strings"
	"time"
)

var (
	base   = envOr("KUAIKE_API_BASE", "https://kuaikejiance.com/open/v1")
	apiKey = os.Getenv("KUAIKE_API_KEY")
	client = &http.Client{Timeout: 30 * time.Second}
)

type envelope struct {
	Code    int             `json:"code"`
	Message string          `json:"message"`
	Data    json.RawMessage `json:"data"`
}

type taskStatus struct {
	TaskID       string         `json:"taskId"`
	Status       string         `json:"status"`
	Total        int            `json:"total"`
	Done         int            `json:"done"`
	Counts       map[string]int `json:"counts"`
	ChargedQuota float64        `json:"chargedQuota"`
}

func envOr(k, d string) string {
	if v := os.Getenv(k); v != "" {
		return v
	}
	return d
}

func requestID() string {
	b := make([]byte, 16)
	rand.Read(b)
	return hex.EncodeToString(b) // 超时重试时用同一个 requestId，不会重复扣额度
}

func call(method, path string, body any, out any) error {
	var payload []byte
	if body != nil {
		payload, _ = json.Marshal(body)
	}
	for attempt := 0; ; attempt++ {
		req, _ := http.NewRequest(method, base+path, bytes.NewReader(payload))
		req.Header.Set("Authorization", "Bearer "+apiKey)
		req.Header.Set("Content-Type", "application/json")
		res, err := client.Do(req)
		if err != nil {
			if attempt < 3 {
				time.Sleep(time.Duration(1<<attempt) * time.Second)
				continue
			}
			return fmt.Errorf("网络异常：%w", err)
		}
		var env envelope
		decodeErr := json.NewDecoder(res.Body).Decode(&env)
		res.Body.Close()
		if (res.StatusCode == 429 || res.StatusCode >= 500) && attempt < 3 {
			time.Sleep(time.Duration(attempt+1) * time.Second)
			continue
		}
		if decodeErr != nil || res.StatusCode >= 400 || env.Code != 0 {
			return fmt.Errorf("HTTP %d code=%d %s", res.StatusCode, env.Code, env.Message)
		}
		if out != nil {
			return json.Unmarshal(env.Data, out)
		}
		return nil
	}
}

func printJSON(v any) {
	b, _ := json.MarshalIndent(v, "", "  ")
	fmt.Println(string(b))
}

func main() {
	if apiKey == "" {
		fmt.Fprintln(os.Stderr, "请先设置 KUAIKE_API_KEY")
		os.Exit(1)
	}
	if len(os.Args) < 2 {
		fmt.Println("用法：go run main.go balance | empty <文件> | empty-plus <文件> | realtime <号码...>")
		return
	}
	var err error
	switch cmd := os.Args[1]; cmd {
	case "balance":
		var d map[string]any
		if err = call("GET", "/balance", nil, &d); err == nil {
			printJSON(d)
		}
	case "realtime":
		var d map[string]any
		if err = call("POST", "/realtime/check", map[string]any{"phones": os.Args[2:], "requestId": requestID()}, &d); err == nil {
			printJSON(d)
		}
	case "empty", "empty-plus":
		f, e := os.Open(os.Args[2])
		if e != nil {
			err = e
			break
		}
		var phones []string
		sc := bufio.NewScanner(f)
		for sc.Scan() {
			if s := strings.TrimSpace(sc.Text()); s != "" {
				phones = append(phones, s)
			}
		}
		f.Close()
		var sub taskStatus
		if err = call("POST", "/"+cmd+"/tasks", map[string]any{"phones": phones, "requestId": requestID()}, &sub); err != nil {
			break
		}
		fmt.Fprintln(os.Stderr, "已提交，任务编号", sub.TaskID)
		var t taskStatus
		for {
			time.Sleep(8 * time.Second)
			if err = call("GET", "/"+cmd+"/tasks/"+sub.TaskID, nil, &t); err != nil {
				break
			}
			fmt.Fprintf(os.Stderr, "  进度 %d/%d  状态 %s\n", t.Done, t.Total, t.Status)
			if t.Status == "done" || t.Status == "failed" {
				break
			}
		}
		if err == nil {
			printJSON(t)
			var r struct {
				Phones []string `json:"phones"`
			}
			if t.Status == "done" {
				if err = call("GET", "/"+cmd+"/tasks/"+sub.TaskID+"/result?kind=empty", nil, &r); err == nil {
					fmt.Fprintf(os.Stderr, "  空号 %d 个\n", len(r.Phones))
				}
			}
		}
	default:
		fmt.Println("未知命令：", cmd)
	}
	if err != nil {
		fmt.Fprintln(os.Stderr, "调用失败：", err)
		os.Exit(1)
	}
}
