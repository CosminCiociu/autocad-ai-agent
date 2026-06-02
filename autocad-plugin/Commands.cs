using System;
using System.IO;

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
        public static int AiExtract(string outPath)
        {
            try
            {
                if (string.IsNullOrWhiteSpace(outPath))
                {
                    outPath = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.DesktopDirectory), "dwg_context.json");
                }

                var ctx = BlockReader.ExtractContext();
                EntitySerializer.WriteContextJson(ctx, outPath);

                Console.WriteLine($"Wrote context to {outPath}");
                return 0;
            }
            catch (Exception ex)
            {
                Console.Error.WriteLine($"AiExtract failed: {ex}");
                return 2;
            }
        }
    }
}
