using System;
using System.Net.Http;
using System.Text;
using Newtonsoft.Json;

namespace AutoCADPlugin
{
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

        public void Dispose()
        {
            _httpClient.Dispose();
        }
    }
}
