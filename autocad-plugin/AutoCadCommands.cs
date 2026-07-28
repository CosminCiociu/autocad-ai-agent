using System;
using Autodesk.AutoCAD.Runtime;

namespace AutoCADPlugin
{
    public class AutoCadCommands
    {
        [CommandMethod("AI_PING")]
        public void AiPingCommand()
        {
            Commands.AiPing();
        }

        [CommandMethod("AI_VERSION")]
        public void AiVersionCommand()
        {
            Commands.AiVersion();
        }

        [CommandMethod("AI_EXTRACT")]
        public void AiExtractCommand(string? outPath = null)
        {
            Commands.AiExtract(outPath ?? string.Empty);
        }

        [CommandMethod("AI_ANALYZE")]
        public void AiAnalyzeCommand(string serverBaseUrl, string userCommand, string? outputPath = null, string? schemaDirectory = null)
        {
            Commands.AiAnalyze(serverBaseUrl, userCommand, outputPath, schemaDirectory);
        }

        [CommandMethod("AI_EXECUTE")]
        public void AiExecuteCommand(string planPath, string? schemaDirectory = null, bool previewOnly = false, string? reportPath = null)
        {
            Commands.AiExecute(planPath, schemaDirectory, previewOnly, reportPath);
        }
    }
}
