// 快客检测 空号检测 API 示例（Java 11+，只用 JDK 自带的 HttpClient）
// 编译运行：
//   export KUAIKE_API_KEY=您的密钥
//   javac KuaikeApiExample.java && java KuaikeApiExample
// 实际项目中建议用 Jackson / Gson 解析 JSON，这里为了不引入依赖，只演示请求和原始返回。
// 接口文档：https://kuaikejiance.com/api-docs
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;
import java.util.List;
import java.util.UUID;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import java.util.stream.Collectors;

public class KuaikeApiExample {
    static final String BASE = System.getenv().getOrDefault("KUAIKE_API_BASE", "https://kuaikejiance.com/open/v1");
    static final String KEY = System.getenv("KUAIKE_API_KEY");
    static final HttpClient HTTP = HttpClient.newBuilder().connectTimeout(Duration.ofSeconds(10)).build();

    static String call(String method, String path, String jsonBody) throws Exception {
        for (int attempt = 0; ; attempt++) {
            HttpRequest.Builder b = HttpRequest.newBuilder(URI.create(BASE + path))
                    .timeout(Duration.ofSeconds(30))
                    .header("Authorization", "Bearer " + KEY)
                    .header("Content-Type", "application/json");
            b = jsonBody == null ? b.GET() : b.method(method, HttpRequest.BodyPublishers.ofString(jsonBody));
            HttpResponse<String> res = HTTP.send(b.build(), HttpResponse.BodyHandlers.ofString());
            int s = res.statusCode();
            if ((s == 429 || s >= 500) && attempt < 3) { Thread.sleep(1000L * (attempt + 1)); continue; }
            if (s >= 400) throw new RuntimeException("HTTP " + s + " " + res.body());
            return res.body();
        }
    }

    static String phonesJson(List<String> phones, String requestId) {
        String arr = phones.stream().map(p -> "\"" + p.replaceAll("[^0-9+]", "") + "\"").collect(Collectors.joining(","));
        return "{\"phones\":[" + arr + "],\"requestId\":\"" + requestId + "\"}";
    }

    static String field(String json, String name) {
        Matcher m = Pattern.compile("\"" + name + "\"\\s*:\\s*\"?([^\",}]*)").matcher(json);
        return m.find() ? m.group(1) : null;
    }

    public static void main(String[] args) throws Exception {
        if (KEY == null || KEY.isEmpty()) throw new IllegalStateException("请先设置 KUAIKE_API_KEY");

        // 1. 查询额度
        System.out.println("额度：" + call("GET", "/balance", null));

        // 2. 实时检测：即查即回（1~20 个号码）
        System.out.println("实时检测：" + call("POST", "/realtime/check",
                phonesJson(List.of("13800138000"), UUID.randomUUID().toString())));

        // 3. 空号检测：提交 → 等待 → 取空号（实际使用时一批至少 2,000 个号码）
        List<String> phones = List.of(/* 从文件或数据库读取号码 */);
        if (!phones.isEmpty()) {
            String requestId = UUID.randomUUID().toString(); // 超时重试时用同一个 requestId，不会重复扣额度
            String taskId = field(call("POST", "/empty/tasks", phonesJson(phones, requestId)), "taskId");
            while (true) {
                String t = call("GET", "/empty/tasks/" + taskId, null);
                String status = field(t, "status");
                System.out.println("进度：" + t);
                if ("done".equals(status) || "failed".equals(status)) break;
                Thread.sleep(8000);
            }
            System.out.println("空号：" + call("GET", "/empty/tasks/" + taskId + "/result?kind=empty", null));
        }
    }
}
