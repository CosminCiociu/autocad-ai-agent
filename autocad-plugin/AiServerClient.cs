using System;
using System.Collections.Generic;
using System.Net.Http;
using System.Text;
using System.Threading.Tasks;
using Newtonsoft.Json;

namespace AutoCADPlugin
{
    public sealed record ChatHistoryEntry(
        [property: JsonProperty("role")] string Role,
        [property: JsonProperty("content")] string Content
    );

    public sealed class ChatResponse
    {
        [JsonProperty("request_id")]
        public string RequestId { get; set; } = string.Empty;

        [JsonProperty("assistant_message")]
        public string AssistantMessage { get; set; } = string.Empty;

        [JsonProperty("action_plan")]
        public ActionPlan ActionPlan { get; set; } = new ActionPlan();
    }

    public sealed class VerificationNodeResult
    {
        [JsonProperty("action_id")]
        public string ActionId { get; set; } = string.Empty;

        [JsonProperty("action_type")]
        public string ActionType { get; set; } = string.Empty;

        [JsonProperty("status")]
        public string Status { get; set; } = string.Empty;

        [JsonProperty("code")]
        public string Code { get; set; } = string.Empty;

        [JsonProperty("message")]
        public string Message { get; set; } = string.Empty;
    }

    public sealed class VerificationResult
    {
        [JsonProperty("request_id")]
        public string RequestId { get; set; } = string.Empty;

        [JsonProperty("status")]
        public string Status { get; set; } = string.Empty;

        [JsonProperty("verified_action_types")]
        public List<string> VerifiedActionTypes { get; set; } = new List<string>();

        [JsonProperty("node_results")]
        public List<VerificationNodeResult> NodeResults { get; set; } = new List<VerificationNodeResult>();
    }

    public sealed class VerifyResponse
    {
        [JsonProperty("request_id")]
        public string RequestId { get; set; } = string.Empty;

        [JsonProperty("verification")]
        public VerificationResult Verification { get; set; } = new VerificationResult();
    }

    public sealed class AiServerClient : IDisposable
    {
        private readonly HttpClient _httpClient;
        private readonly string _baseUrl;

        public AiServerClient(string baseUrl)
        {
            if (string.IsNullOrWhiteSpace(baseUrl))
            {
                throw new ArgumentException("Base URL must be provided.", nameof(baseUrl));
            }

            _baseUrl = baseUrl.TrimEnd('/');
            _httpClient = new HttpClient();
        }

        public ActionPlan Analyze(DwgContext context, string userCommand)
        {
            var json = JsonConvert.SerializeObject(context, Formatting.None, new JsonSerializerSettings { NullValueHandling = NullValueHandling.Ignore });
            var content = new StringContent(json, Encoding.UTF8, "application/json");
            var url = new Uri(new Uri(_baseUrl), "/analyze");
            using var request = new HttpRequestMessage(HttpMethod.Post, url)
            {
                Content = content
            };
            request.Headers.Add("x-user-command", userCommand ?? string.Empty);

            var response = _httpClient.SendAsync(request).GetAwaiter().GetResult();
            response.EnsureSuccessStatusCode();

            var body = response.Content.ReadAsStringAsync().GetAwaiter().GetResult();
            return JsonConvert.DeserializeObject<ActionPlan>(body) ?? throw new InvalidOperationException("Could not deserialize action plan.");
        }

        public ChatResponse Chat(DwgContext context, IReadOnlyList<ChatHistoryEntry> history)
        {
            var requestPayload = new
            {
                request_id = context.RequestId,
                schema_version = context.SchemaVersion,
                context,
                messages = history
            };
            var json = JsonConvert.SerializeObject(requestPayload, Formatting.None, new JsonSerializerSettings { NullValueHandling = NullValueHandling.Ignore });
            var content = new StringContent(json, Encoding.UTF8, "application/json");
            var url = new Uri(new Uri(_baseUrl), "/chat");
            using var request = new HttpRequestMessage(HttpMethod.Post, url)
            {
                Content = content
            };

            var response = _httpClient.SendAsync(request).GetAwaiter().GetResult();
            if (!response.IsSuccessStatusCode)
            {
                var errorBody = response.Content.ReadAsStringAsync().GetAwaiter().GetResult();
                throw new InvalidOperationException($"Server returned {response.StatusCode}: {errorBody}");
            }

            var body = response.Content.ReadAsStringAsync().GetAwaiter().GetResult();
            return JsonConvert.DeserializeObject<ChatResponse>(body) ?? throw new InvalidOperationException("Could not deserialize chat response.");
        }

        public VerifyResponse Verify(
            ActionPlan actionPlan,
            DwgContext contextBefore,
            DwgContext contextAfter,
            ExecutionReport executionReport,
            string userCommand)
        {
            var requestPayload = new
            {
                action_plan = actionPlan,
                context_before = contextBefore,
                context_after = contextAfter,
                execution_report = executionReport,
                user_command = userCommand ?? string.Empty,
            };

            var json = JsonConvert.SerializeObject(requestPayload, Formatting.None, new JsonSerializerSettings { NullValueHandling = NullValueHandling.Ignore });
            var content = new StringContent(json, Encoding.UTF8, "application/json");
            var url = new Uri(new Uri(_baseUrl), "/verify");
            using var request = new HttpRequestMessage(HttpMethod.Post, url)
            {
                Content = content
            };

            var response = _httpClient.SendAsync(request).GetAwaiter().GetResult();
            if (!response.IsSuccessStatusCode)
            {
                var errorBody = response.Content.ReadAsStringAsync().GetAwaiter().GetResult();
                throw new InvalidOperationException($"Server returned {response.StatusCode}: {errorBody}");
            }

            var body = response.Content.ReadAsStringAsync().GetAwaiter().GetResult();
            return JsonConvert.DeserializeObject<VerifyResponse>(body) ?? throw new InvalidOperationException("Could not deserialize verify response.");
        }

        public void Dispose()
        {
            _httpClient.Dispose();
        }
    }
}
