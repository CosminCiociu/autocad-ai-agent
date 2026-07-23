using System;
using System.Collections.Generic;
using System.Drawing;
using System.IO;
using System.Linq;
using System.Net.Http;
using System.Text;
using System.Windows.Forms;
using Newtonsoft.Json;

namespace AutoCADPlugin
{
    public sealed record ChatMessage(string Sender, string Content, DateTime Timestamp)
    {
        [JsonIgnore]
        public string Role => Sender switch
        {
            "User" => "user",
            "AI" => "assistant",
            _ => "system",
        };
    }

    public class ChatPanel : Form
    {
        private readonly TextBox _inputBox;
        private readonly Button _sendButton;
        private readonly Button _analyzeButton;
        private readonly Button _previewButton;
        private readonly Button _executeButton;
        private readonly Button _copyButton;
        private readonly RichTextBox _historyBox;
        private readonly TextBox _serverUrlBox;
        private readonly TextBox _schemaDirBox;
        private readonly Button _healthButton;
        private readonly Label _statusLabel;
        private readonly List<ChatMessage> _messages;
        private readonly string _sessionPath;
        private ActionPlan? _lastActionPlan;

        public ChatPanel()
        {
            Text = "AutoCAD AI Chat";
            Width = 680;
            Height = 520;
            FormBorderStyle = FormBorderStyle.FixedDialog;
            MaximizeBox = false;
            MinimizeBox = true;

            _historyBox = new RichTextBox
            {
                Location = new Point(12, 12),
                Size = new Size(640, 280),
                ReadOnly = true,
                Anchor = AnchorStyles.Top | AnchorStyles.Left | AnchorStyles.Right
            };
            Controls.Add(_historyBox);

            _inputBox = new TextBox
            {
                Location = new Point(12, 300),
                Size = new Size(520, 24),
                Anchor = AnchorStyles.Bottom | AnchorStyles.Left | AnchorStyles.Right
            };
            Controls.Add(_inputBox);

            _sendButton = new Button
            {
                Text = "Trimite",
                Location = new Point(540, 300),
                Size = new Size(112, 26),
                Anchor = AnchorStyles.Bottom | AnchorStyles.Right
            };
            _sendButton.Click += SendButton_Click;
            Controls.Add(_sendButton);

            _serverUrlBox = new TextBox
            {
                Location = new Point(12, 340),
                Size = new Size(520, 24),
                Text = "http://127.0.0.1:8001",
                Anchor = AnchorStyles.Bottom | AnchorStyles.Left | AnchorStyles.Right
            };
            Controls.Add(_serverUrlBox);

            _schemaDirBox = new TextBox
            {
                Location = new Point(12, 372),
                Size = new Size(520, 24),
                Text = "..\\shared\\schemas",
                Anchor = AnchorStyles.Bottom | AnchorStyles.Left | AnchorStyles.Right
            };
            Controls.Add(_schemaDirBox);

            _analyzeButton = new Button
            {
                Text = "Analyze",
                Location = new Point(540, 340),
                Size = new Size(112, 26),
                Anchor = AnchorStyles.Bottom | AnchorStyles.Right
            };
            _analyzeButton.Click += AnalyzeButton_Click;
            Controls.Add(_analyzeButton);

            _previewButton = new Button
            {
                Text = "Preview",
                Location = new Point(540, 372),
                Size = new Size(112, 26),
                Anchor = AnchorStyles.Bottom | AnchorStyles.Right
            };
            _previewButton.Click += PreviewButton_Click;
            Controls.Add(_previewButton);

            _executeButton = new Button
            {
                Text = "Execute",
                Location = new Point(540, 404),
                Size = new Size(112, 26),
                Anchor = AnchorStyles.Bottom | AnchorStyles.Right
            };
            _executeButton.Click += ExecuteButton_Click;
            Controls.Add(_executeButton);

            _copyButton = new Button
            {
                Text = "📋 Copy",
                Location = new Point(540, 436),
                Size = new Size(112, 26),
                Anchor = AnchorStyles.Bottom | AnchorStyles.Right
            };
            _copyButton.Click += CopyButton_Click;
            Controls.Add(_copyButton);

            _healthButton = new Button
            {
                Text = "Health",
                Location = new Point(540, 468),
                Size = new Size(112, 26),
                Anchor = AnchorStyles.Bottom | AnchorStyles.Right
            };
            _healthButton.Click += HealthButton_Click;
            Controls.Add(_healthButton);

            var serverLabel = new Label
            {
                Text = "AI Server URL:",
                Location = new Point(12, 322),
                AutoSize = true
            };
            Controls.Add(serverLabel);

            _statusLabel = new Label
            {
                Text = "Server status: unknown",
                Location = new Point(12, 400),
                Size = new Size(520, 20),
                Anchor = AnchorStyles.Bottom | AnchorStyles.Left | AnchorStyles.Right
            };
            Controls.Add(_statusLabel);

            var schemaLabel = new Label
            {
                Text = "Schema directory:",
                Location = new Point(12, 354),
                AutoSize = true
            };
            Controls.Add(schemaLabel);

            _messages = new List<ChatMessage>();
            _sessionPath = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "ai_chat_session.json");
            LoadSession();
            UpdateServerStatus("unknown");
        }

        private void LogChatMessage(string sender, string message)
        {
            if (message == null)
            {
                message = string.Empty;
            }

            var chatMessage = new ChatMessage(sender, message, DateTime.Now);
            _messages.Add(chatMessage);
            AppendMessage(chatMessage);
            SaveSession();
        }

        private void LogSystemMessage(string message)
        {
            var systemMessage = new ChatMessage("System", message, DateTime.Now);
            _messages.Add(systemMessage);
            AppendMessage(systemMessage);
            SaveSession();
        }

        private void AppendMessage(ChatMessage message)
        {
            // Use colored formatting based on sender
            if (message.Sender == "User")
            {
                AppendColoredText($"[{message.Timestamp:HH:mm:ss}] ", Color.Gray);
                AppendColoredText("👤 User: ", Color.Blue, bold: true);
                AppendColoredText(message.Content + Environment.NewLine, Color.Blue);
            }
            else if (message.Sender == "AI")
            {
                AppendColoredText($"[{message.Timestamp:HH:mm:ss}] ", Color.Gray);
                AppendColoredText("🤖 AI: ", Color.Green, bold: true);
                AppendColoredText(message.Content + Environment.NewLine, Color.Green);
                AppendColoredText(new string('—', 80) + Environment.NewLine, Color.LightGray);
            }
            else if (message.Sender == "System")
            {
                AppendColoredText($"[{message.Timestamp:HH:mm:ss}] ", Color.Gray);
                AppendColoredText("⚙️ System: ", Color.Gray, bold: false, italic: true);
                AppendColoredText(message.Content + Environment.NewLine, Color.DarkGray, italic: true);
            }
            _historyBox.ScrollToCaret();
        }

        private void AppendColoredText(string text, Color color, bool bold = false, bool italic = false)
        {
            int startIndex = _historyBox.Text.Length;
            _historyBox.AppendText(text);
            int endIndex = _historyBox.Text.Length;

            _historyBox.Select(startIndex, endIndex - startIndex);
            _historyBox.SelectionColor = color;
            if (bold)
            {
                _historyBox.SelectionFont = new Font(_historyBox.Font, FontStyle.Bold);
            }
            if (italic)
            {
                _historyBox.SelectionFont = new Font(_historyBox.Font, FontStyle.Italic);
            }
            _historyBox.Select(_historyBox.Text.Length, 0);
        }

        private void ProcessPrompt(string? prompt)
        {
            if (prompt is null || string.IsNullOrWhiteSpace(prompt))
            {
                return;
            }

            LogChatMessage("User", prompt);

            var serverUrl = _serverUrlBox.Text?.Trim() ?? string.Empty;
            if (string.IsNullOrWhiteSpace(serverUrl))
            {
                MessageBox.Show("Introduceți URL-ul serverului AI.", "Atenție", MessageBoxButtons.OK, MessageBoxIcon.Warning);
                return;
            }

            var response = SendChatRequest(serverUrl, prompt);
            if (response != null)
            {
                _lastActionPlan = response.ActionPlan;
                LogSystemMessage($"✓ Request sent to: {NormalizeServerUrl(serverUrl)}/chat");
                LogChatMessage("AI", response.AssistantMessage ?? "");
                string actionIcon = _lastActionPlan.Actions.Count > 0 ? "📋" : "ℹ️";
                LogSystemMessage($"{actionIcon} Plan generat: {_lastActionPlan.Actions.Count} acțiuni");
                LogSystemMessage(JsonConvert.SerializeObject(_lastActionPlan, Formatting.Indented) ?? string.Empty);

                if (_lastActionPlan.NeedsClarification)
                {
                    LogChatMessage("AI", _lastActionPlan.ClarificationQuestion ?? "AI cere clarificare.");
                }
            }
        }

        private void LoadSession()
        {
            if (!File.Exists(_sessionPath))
            {
                return;
            }

            try
            {
                var text = File.ReadAllText(_sessionPath);
                var saved = JsonConvert.DeserializeObject<List<ChatMessage>>(text);
                if (saved == null)
                {
                    return;
                }

                _messages.AddRange(saved);
                foreach (var message in saved)
                {
                    AppendMessage(message);
                }
            }
            catch
            {
                // ignore corrupt session files
            }
        }

        private void SaveSession()
        {
            try
            {
                var text = JsonConvert.SerializeObject(_messages, Formatting.Indented);
                File.WriteAllText(_sessionPath, text);
            }
            catch
            {
                // ignore save failures for now
            }
        }

        private static string NormalizeServerUrl(string? rawUrl)
        {
            if (string.IsNullOrWhiteSpace(rawUrl))
            {
                return string.Empty;
            }

            var normalized = rawUrl!.Trim().TrimEnd('/');
            if (normalized.EndsWith("/chat", StringComparison.OrdinalIgnoreCase))
            {
                normalized = normalized.Substring(0, normalized.Length - "/chat".Length);
            }

            return normalized;
        }

        private void UpdateServerStatus(string status)
        {
            string emoji = status switch
            {
                "ok" => "✅",
                "offline" => "❌",
                _ => "❓"
            };
            _statusLabel.Text = $"{emoji} Server status: {status}";
            _statusLabel.ForeColor = status == "ok" ? Color.Green : Color.Red;
            _statusLabel.Font = new Font(_statusLabel.Font, FontStyle.Bold);
        }

        private async void HealthButton_Click(object sender, EventArgs e)
        {
            var serverUrl = NormalizeServerUrl(_serverUrlBox.Text);
            if (string.IsNullOrWhiteSpace(serverUrl))
            {
                MessageBox.Show("Introduceți URL-ul serverului AI.", "Atenție", MessageBoxButtons.OK, MessageBoxIcon.Warning);
                return;
            }

            try
            {
                using var client = new HttpClient();
                var response = await client.GetAsync(new Uri(new Uri(serverUrl), "/health"));
                if (response.IsSuccessStatusCode)
                {
                    UpdateServerStatus("ok");
                    LogSystemMessage("✅ Server is responsive.");
                }
                else
                {
                    UpdateServerStatus("offline");
                    LogSystemMessage($"❌ Server health failed: {response.StatusCode}");
                }
            }
            catch (Exception ex)
            {
                UpdateServerStatus("offline");
                MessageBox.Show($"Nu se poate accesa serverul AI: {ex.Message}", "Eroare", MessageBoxButtons.OK, MessageBoxIcon.Error);
                LogSystemMessage($"❌ Server health error: {ex.Message}");
            }
        }

        private void SendButton_Click(object sender, EventArgs e)
        {
            var prompt = _inputBox.Text?.Trim();
            if (string.IsNullOrWhiteSpace(prompt))
            {
                MessageBox.Show("Introduceți ceva text înainte de a trimite.", "Atenție", MessageBoxButtons.OK, MessageBoxIcon.Warning);
                return;
            }

            ProcessPrompt(prompt);
            _inputBox.Clear();
        }

        private void AnalyzeButton_Click(object sender, EventArgs e)
        {
            var prompt = _inputBox.Text?.Trim();
            if (string.IsNullOrWhiteSpace(prompt))
            {
                MessageBox.Show("Introduceți promptul pentru analiză.", "Atenție", MessageBoxButtons.OK, MessageBoxIcon.Warning);
                return;
            }

            ProcessPrompt(prompt);
            _inputBox.Clear();
        }

        private void CopyButton_Click(object sender, EventArgs e)
        {
            var lastAiMessage = _messages.LastOrDefault(m => m.Sender == "AI");
            if (lastAiMessage == null)
            {
                MessageBox.Show("Nu este niciun răspuns AI de copiat.", "Atenție", MessageBoxButtons.OK, MessageBoxIcon.Information);
                return;
            }

            try
            {
                Clipboard.SetText(lastAiMessage.Content);
                LogSystemMessage("✅ Răspunsul AI a fost copiat în clipboard.");
            }
            catch (Exception ex)
            {
                MessageBox.Show($"Eroare la copiere: {ex.Message}", "Eroare", MessageBoxButtons.OK, MessageBoxIcon.Error);
            }
        }

        private void PreviewButton_Click(object sender, EventArgs e)
        {
            if (_lastActionPlan == null)
            {
                MessageBox.Show("Nu există un plan încărcat. Apăsați mai întâi Analyze.", "Atenție", MessageBoxButtons.OK, MessageBoxIcon.Warning);
                return;
            }

            var ctx = BlockReader.ExtractContext();
            var report = ActionExecutor.ExecuteActionPlan(_lastActionPlan, ctx, previewOnly: true);
            LogSystemMessage("Preview generat.");
            LogSystemMessage(JsonConvert.SerializeObject(report, Formatting.Indented) ?? string.Empty);
        }

        private void ExecuteButton_Click(object sender, EventArgs e)
        {
            if (_lastActionPlan == null)
            {
                MessageBox.Show("Nu există un plan încărcat. Apăsați mai întâi Analyze.", "Atenție", MessageBoxButtons.OK, MessageBoxIcon.Warning);
                return;
            }

            var ctx = BlockReader.ExtractContext();
            var report = ActionExecutor.ExecuteActionPlan(_lastActionPlan, ctx, previewOnly: false);
            LogSystemMessage("Execuție completă generată.");
            LogSystemMessage(JsonConvert.SerializeObject(report, Formatting.Indented) ?? string.Empty);
        }

        private ActionPlan? LoadActionPlanFromPrompt()
        {
            MessageBox.Show("Funcția LoadActionPlanFromPrompt nu este utilizată în acest UI. Folosiți Analyze pentru a genera un plan.", "Info", MessageBoxButtons.OK, MessageBoxIcon.Information);
            return null;
        }

        private void SavePayload(string payloadType, string requestId, object payload)
        {
            try
            {
                var payloadDir = @"E:\Ai agent\ai-server\payloads";
                if (!Directory.Exists(payloadDir))
                {
                    Directory.CreateDirectory(payloadDir);
                }

                var timestamp = DateTime.Now.ToString("yyyy-MM-dd_HH-mm-ss-fff");
                var filename = $"{timestamp}_{requestId}_{payloadType}.json";
                var filepath = Path.Combine(payloadDir, filename);

                var json = JsonConvert.SerializeObject(payload, Formatting.Indented);
                File.WriteAllText(filepath, json);
            }
            catch (Exception ex)
            {
                LogSystemMessage($"⚠️ Failed to save payload: {ex.Message}");
            }
        }

        private ChatResponse? SendChatRequest(string serverUrl, string prompt)
        {
            try
            {
                var normalizedServerUrl = NormalizeServerUrl(serverUrl);
                LogSystemMessage($"Calling AI server at: {normalizedServerUrl}/chat");

                var ctx = BlockReader.ExtractContext();
                LogSystemMessage("Extracted DWG context for AI request.");

                using var client = new AiServerClient(normalizedServerUrl);
                var history = _messages
                    .Where(m => m.Role == "user" || m.Role == "assistant" || m.Role == "system")
                    .Select(m => new ChatHistoryEntry(m.Role, m.Content))
                    .ToList();
                history.Add(new ChatHistoryEntry("user", prompt ?? string.Empty));

                // Save request payload
                var requestPayload = new
                {
                    request_id = ctx.RequestId,
                    timestamp = DateTime.Now.ToString("o"),
                    schema_version = ctx.SchemaVersion,
                    context = ctx,
                    messages = history
                };
                SavePayload("request", ctx.RequestId, requestPayload);

                var response = client.Chat(ctx, history);

                if (response != null)
                {
                    // Save response payload
                    var responsePayload = new
                    {
                        request_id = response.RequestId,
                        timestamp = DateTime.Now.ToString("o"),
                        assistant_message = response.AssistantMessage,
                        action_plan = response.ActionPlan
                    };
                    SavePayload("response", response.RequestId, responsePayload);
                    LogSystemMessage($"📁 Payloads saved to: E:\\Ai agent\\ai-server\\payloads\\");
                }

                return response;
            }
            catch (Exception ex)
            {
                MessageBox.Show($"Eroare la chat: {ex.Message}", "Eroare", MessageBoxButtons.OK, MessageBoxIcon.Error);
                return null;
            }
        }
    }
}
