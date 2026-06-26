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
            var content = new StringContent(JsonConvert.SerializeObject(context), Encoding.UTF8, "application/json");
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
                context,
                messages = history
            };
            var content = new StringContent(JsonConvert.SerializeObject(requestPayload), Encoding.UTF8, "application/json");
            var url = new Uri(new Uri(_baseUrl), "/chat");
            using var request = new HttpRequestMessage(HttpMethod.Post, url)
            {
                Content = content
            };

            var response = _httpClient.SendAsync(request).GetAwaiter().GetResult();
            response.EnsureSuccessStatusCode();

            var body = response.Content.ReadAsStringAsync().GetAwaiter().GetResult();
            return JsonConvert.DeserializeObject<ChatResponse>(body) ?? throw new InvalidOperationException("Could not deserialize chat response.");
        }

        public void Dispose()
        {
            _httpClient.Dispose();
        }
    }
}
