<?php
// 快客检测 空号检测 API 示例（PHP 7.4+，需要 curl 扩展）
// 用法：
//   export KUAIKE_API_KEY=您的密钥
//   php kuaike_api.php balance
//   php kuaike_api.php empty numbers.txt      # 空号检测（每行一个号码，至少 2000 个）
//   php kuaike_api.php realtime 13800138000   # 实时检测，即查即回
// 接口文档：https://kuaikejiance.com/api-docs

const KUAIKE_BASE = 'https://kuaikejiance.com/open/v1';

function kuaike_call(string $method, string $path, ?array $body = null, int $retries = 3): array
{
    $key = getenv('KUAIKE_API_KEY');
    if (!$key) {
        throw new RuntimeException('请先设置 KUAIKE_API_KEY');
    }
    $base = getenv('KUAIKE_API_BASE') ?: KUAIKE_BASE;
    for ($attempt = 0; ; $attempt++) {
        $ch = curl_init($base . $path);
        curl_setopt_array($ch, [
            CURLOPT_CUSTOMREQUEST => $method,
            CURLOPT_RETURNTRANSFER => true,
            CURLOPT_TIMEOUT => 30,
            CURLOPT_HTTPHEADER => ['Authorization: Bearer ' . $key, 'Content-Type: application/json'],
        ]);
        if ($body !== null) {
            curl_setopt($ch, CURLOPT_POSTFIELDS, json_encode($body, JSON_UNESCAPED_UNICODE));
        }
        $raw = curl_exec($ch);
        $status = (int) curl_getinfo($ch, CURLINFO_HTTP_CODE);
        $err = curl_error($ch);
        curl_close($ch);
        if ($raw === false && $attempt < $retries) { sleep(1 << $attempt); continue; }
        if (($status === 429 || $status >= 500) && $attempt < $retries) { sleep($attempt + 1); continue; }
        if ($raw === false) {
            throw new RuntimeException('网络异常：' . $err);
        }
        $json = json_decode($raw, true);
        if ($status >= 400 || !is_array($json) || ($json['code'] ?? -1) !== 0) {
            throw new RuntimeException("HTTP {$status} code=" . ($json['code'] ?? '') . ' ' . ($json['message'] ?? $raw));
        }
        return $json['data'];
    }
}

function kuaike_request_id(): string
{
    return bin2hex(random_bytes(16)); // 超时重试时用同一个 requestId，不会重复扣额度
}

$cmd = $argv[1] ?? '';
try {
    if ($cmd === 'balance') {
        print_r(kuaike_call('GET', '/balance'));
    } elseif ($cmd === 'empty' || $cmd === 'empty-plus') {
        $phones = array_values(array_filter(array_map('trim', file($argv[2]))));
        $taskId = kuaike_call('POST', "/{$cmd}/tasks", ['phones' => $phones, 'requestId' => kuaike_request_id()])['taskId'];
        fwrite(STDERR, "已提交，任务编号 {$taskId}\n");
        do {
            sleep(8);
            $t = kuaike_call('GET', "/{$cmd}/tasks/{$taskId}");
            fwrite(STDERR, "  进度 {$t['done']}/{$t['total']}  状态 {$t['status']}\n");
        } while (!in_array($t['status'], ['done', 'failed'], true));
        print_r($t);
        if ($t['status'] === 'done') {
            $empty = kuaike_call('GET', "/{$cmd}/tasks/{$taskId}/result?kind=empty")['phones'];
            file_put_contents("{$taskId}_empty.txt", implode("\n", $empty) . "\n");
            fwrite(STDERR, '  空号 ' . count($empty) . " 个 → {$taskId}_empty.txt\n");
        }
    } elseif ($cmd === 'realtime') {
        print_r(kuaike_call('POST', '/realtime/check', ['phones' => array_slice($argv, 2), 'requestId' => kuaike_request_id()]));
    } else {
        echo "用法：php kuaike_api.php balance | empty <文件> | empty-plus <文件> | realtime <号码...>\n";
    }
} catch (RuntimeException $e) {
    fwrite(STDERR, '调用失败：' . $e->getMessage() . "\n");
    exit(1);
}
