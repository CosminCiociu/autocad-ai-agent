using Newtonsoft.Json;
using Newtonsoft.Json.Linq;
using System.Collections.Generic;

namespace AutoCADPlugin
{
    public class ActionPlan
    {
        [JsonProperty("schema_version")]
        public string SchemaVersion { get; set; } = string.Empty;

        [JsonProperty("request_id")]
        public string RequestId { get; set; } = string.Empty;

        [JsonProperty("summary")]
        public string? Summary { get; set; }

        [JsonProperty("needs_clarification")]
        public bool NeedsClarification { get; set; }

        [JsonProperty("clarification_question")]
        public string? ClarificationQuestion { get; set; }

        [JsonProperty("actions")]
        public List<ActionItem> Actions { get; set; } = new List<ActionItem>();
    }

    public class ActionItem
    {
        [JsonProperty("id")]
        public string Id { get; set; } = string.Empty;

        [JsonProperty("type")]
        public string Type { get; set; } = string.Empty;

        [JsonProperty("reason")]
        public string? Reason { get; set; }

        [JsonProperty("args")]
        public JObject Args { get; set; } = new JObject();
    }
}
