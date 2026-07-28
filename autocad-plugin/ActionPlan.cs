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

        [JsonProperty("goal_plan")]
        public GoalPlan? GoalPlan { get; set; }

        [JsonProperty("task_graph")]
        public TaskGraph? TaskGraph { get; set; }
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

    public class GoalPlan
    {
        [JsonProperty("version")]
        public string Version { get; set; } = string.Empty;

        [JsonProperty("goal")]
        public string Goal { get; set; } = string.Empty;

        [JsonProperty("status")]
        public string Status { get; set; } = string.Empty;

        [JsonProperty("subgoals")]
        public List<GoalSubgoal> Subgoals { get; set; } = new List<GoalSubgoal>();
    }

    public class GoalSubgoal
    {
        [JsonProperty("id")]
        public string Id { get; set; } = string.Empty;

        [JsonProperty("title")]
        public string Title { get; set; } = string.Empty;

        [JsonProperty("status")]
        public string Status { get; set; } = string.Empty;

        [JsonProperty("kind")]
        public string Kind { get; set; } = string.Empty;

        [JsonProperty("action_id")]
        public string? ActionId { get; set; }
    }

    public class TaskGraph
    {
        [JsonProperty("version")]
        public string Version { get; set; } = string.Empty;

        [JsonProperty("entrypoints")]
        public List<string> Entrypoints { get; set; } = new List<string>();

        [JsonProperty("terminal_nodes")]
        public List<string> TerminalNodes { get; set; } = new List<string>();

        [JsonProperty("execution_order")]
        public List<string> ExecutionOrder { get; set; } = new List<string>();

        [JsonProperty("nodes")]
        public List<TaskNode> Nodes { get; set; } = new List<TaskNode>();

        [JsonProperty("edges")]
        public List<TaskEdge> Edges { get; set; } = new List<TaskEdge>();
    }

    public class TaskNode
    {
        [JsonProperty("id")]
        public string Id { get; set; } = string.Empty;

        [JsonProperty("title")]
        public string Title { get; set; } = string.Empty;

        [JsonProperty("kind")]
        public string Kind { get; set; } = string.Empty;

        [JsonProperty("status")]
        public string Status { get; set; } = string.Empty;

        [JsonProperty("action_id")]
        public string? ActionId { get; set; }

        [JsonProperty("depends_on")]
        public List<string> DependsOn { get; set; } = new List<string>();
    }

    public class TaskEdge
    {
        [JsonProperty("from")]
        public string From { get; set; } = string.Empty;

        [JsonProperty("to")]
        public string To { get; set; } = string.Empty;

        [JsonProperty("type")]
        public string Type { get; set; } = string.Empty;
    }
}
