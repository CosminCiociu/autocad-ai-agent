using System;
using System.IO;
using Newtonsoft.Json;
using AutocadAiAgent.SchemaValidation;

// This is a lightweight scaffold for an AutoCAD plugin command that
// extracts drawing context and writes it to a JSON file. Replace the
// placeholder methods with actual AutoCAD API calls (AutoCAD .NET API / ObjectARX).

namespace AutoCADPlugin
{
    public static class Commands
    {
        // Entry point called by user: AI_PING
        public static int AiPing()
        {
            Console.WriteLine("AI plugin alive and ready.");
            return 0;
        }

        // Entry point called by user: AI_EXTRACT
        // Example usage (pseudo): AI_EXTRACT C:\temp\out.json
        public static int AiExtract(string outPath, string? schemaDirectory = null)
        {
            try
            {
                if (string.IsNullOrWhiteSpace(outPath))
                {
                    outPath = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.DesktopDirectory), "dwg_context.json");
                }

                var ctx = BlockReader.ExtractContext();
                var json = JsonConvert.SerializeObject(ctx, Formatting.Indented, new JsonSerializerSettings { NullValueHandling = NullValueHandling.Ignore });

                if (!string.IsNullOrWhiteSpace(schemaDirectory))
                {
                    var validator = new SchemaValidator(schemaDirectory!);
                    var validation = validator.ValidateDwgContext(json);
                    if (!validation.IsValid)
                    {
                        Console.Error.WriteLine("Context JSON validation failed:\n" + string.Join("\n", validation.Errors));
                        return 2;
                    }
                }

                File.WriteAllText(outPath, json);
                Console.WriteLine($"Wrote context to {outPath}");
                return 0;
            }
            catch (Exception ex)
            {
                Console.Error.WriteLine($"AiExtract failed: {ex}");
                return 2;
            }
        }

        // Entry point called by user: AI_ANALYZE
        // Example usage (pseudo): AI_ANALYZE http://127.0.0.1:8001 x-user-command="insert block"
        public static int AiAnalyze(string serverBaseUrl, string userCommand, string? outputPath = null, string? schemaDirectory = null)
        {
            try
            {
                var ctx = BlockReader.ExtractContext();
                var json = JsonConvert.SerializeObject(ctx, Formatting.Indented, new JsonSerializerSettings { NullValueHandling = NullValueHandling.Ignore });

                if (!string.IsNullOrWhiteSpace(schemaDirectory))
                {
                    var validator = new SchemaValidator(schemaDirectory!);
                    var validation = validator.ValidateDwgContext(json);
                    if (!validation.IsValid)
                    {
                        Console.Error.WriteLine("Context JSON validation failed before sending to AI server:\n" + string.Join("\n", validation.Errors));
                        return 2;
                    }
                }

                using var client = new AiServerClient(serverBaseUrl);
                var plan = client.Analyze(ctx, userCommand);

                var resolvedOutputPath = string.IsNullOrWhiteSpace(outputPath)
                    ? Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.DesktopDirectory), "action_plan.json")
                    : outputPath!;

                EntitySerializer.WriteActionPlanJson(plan, resolvedOutputPath);
                Console.WriteLine($"Wrote action plan to {resolvedOutputPath}");
                return 0;
            }
            catch (Exception ex)
            {
                Console.Error.WriteLine($"AiAnalyze failed: {ex}");
                return 2;
            }
        }

        // Entry point called by user: AI_EXECUTE
        // Example usage (pseudo): AI_EXECUTE C:\temp\action_plan.json
        public static int AiExecute(string planPath, string? schemaDirectory = null, bool previewOnly = false, string? reportPath = null)
        {
            try
            {
                if (string.IsNullOrWhiteSpace(planPath) || !File.Exists(planPath))
                {
                    Console.Error.WriteLine("Plan path is invalid or does not exist.");
                    return 2;
                }

                var body = File.ReadAllText(planPath);

                if (!string.IsNullOrWhiteSpace(schemaDirectory))
                {
                    var validator = new SchemaValidator(schemaDirectory!);
                    var validation = validator.ValidateActionPlan(body);
                    if (!validation.IsValid)
                    {
                        Console.Error.WriteLine("Action plan JSON validation failed before execution:\n" + string.Join("\n", validation.Errors));
                        return 2;
                    }
                }

                var plan = JsonConvert.DeserializeObject<ActionPlan>(body);
                if (plan == null)
                {
                    Console.Error.WriteLine("Failed to parse action plan.");
                    return 2;
                }

                var ctx = BlockReader.ExtractContext();
                var report = ActionExecutor.ExecuteActionPlan(plan, ctx, previewOnly);

                var resolvedReportPath = string.IsNullOrWhiteSpace(reportPath)
                    ? Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.DesktopDirectory), "execution_report.json")
                    : reportPath!;

                EntitySerializer.WriteExecutionReportJson(report, resolvedReportPath);
                Console.WriteLine(previewOnly ? "Previewed action plan." : "Executed action plan.");
                return 0;
            }
            catch (Exception ex)
            {
                Console.Error.WriteLine($"AiExecute failed: {ex}");
                return 2;
            }
        }
    }
}
