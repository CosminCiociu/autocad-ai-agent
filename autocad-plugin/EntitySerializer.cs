using System;
using System.IO;
using Newtonsoft.Json;

namespace AutoCADPlugin
{
    public static class EntitySerializer
    {
        public static void WriteContextJson(object context, string outPath)
        {
            var dir = Path.GetDirectoryName(outPath);
            if (!string.IsNullOrEmpty(dir) && !Directory.Exists(dir))
            {
                Directory.CreateDirectory(dir);
            }

            var json = JsonConvert.SerializeObject(context, Formatting.Indented);
            File.WriteAllText(outPath, json);
        }

        public static void WriteActionPlanJson(ActionPlan plan, string outPath)
        {
            var dir = Path.GetDirectoryName(outPath);
            if (!string.IsNullOrEmpty(dir) && !Directory.Exists(dir))
            {
                Directory.CreateDirectory(dir);
            }

            var json = JsonConvert.SerializeObject(plan, Formatting.Indented);
            File.WriteAllText(outPath, json);
        }

        public static void WriteExecutionReportJson(ExecutionReport report, string outPath)
        {
            var dir = Path.GetDirectoryName(outPath);
            if (!string.IsNullOrEmpty(dir) && !Directory.Exists(dir))
            {
                Directory.CreateDirectory(dir);
            }

            var json = JsonConvert.SerializeObject(report, Formatting.Indented);
            File.WriteAllText(outPath, json);
        }
    }
}
