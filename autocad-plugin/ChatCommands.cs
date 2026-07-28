using System;
using Autodesk.AutoCAD.Runtime;
using Exception = System.Exception;

namespace AutoCADPlugin
{
    public class ChatCommands
    {
        [CommandMethod("AI_CHAT")]
        [CommandMethod("AI_OPEN_CHAT")]
        public void AiChat()
        {
            try
            {
                var chat = new ChatPanel();
                chat.Show();
            }
            catch (Exception ex)
            {
                Console.Error.WriteLine($"AI_CHAT failed: {ex}");
            }
        }
    }
}
