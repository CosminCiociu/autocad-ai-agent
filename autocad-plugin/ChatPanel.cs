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
                Text = "http://127.0.0.1:8000",
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

            _healthButton = new Button
            {
                Text = "Health",
                Location = new Point(540, 436),
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
            _historyBox.AppendText($"[{message.Timestamp:HH:mm:ss}] {message.Sender}: {message.Content}" + Environment.NewLine);
            _historyBox.ScrollToCaret();
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
                LogChatMessage("AI", response.AssistantMessage ?? "");
                LogSystemMessage($"Plan generat: {_lastActionPlan.Actions.Count} acțiuni");
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

        private void UpdateServerStatus(string status)
        {
            _statusLabel.Text = $"Server status: {status}";
            _statusLabel.ForeColor = status == "ok" ? Color.Green : Color.Red;
        }

        private async void HealthButton_Click(object sender, EventArgs e)
        {
            var serverUrl = _serverUrlBox.Text?.Trim() ?? string.Empty;
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
                    LogSystemMessage("Server health OK.");
                }
                else
                {
                    UpdateServerStatus("unhealthy");
                    LogSystemMessage($"Server health failed: {response.StatusCode}");
                }
            }
            catch (Exception ex)
            {
                UpdateServerStatus("offline");
                MessageBox.Show($"Nu se poate accesa serverul AI: {ex.Message}", "Eroare", MessageBoxButtons.OK, MessageBoxIcon.Error);
                LogSystemMessage($"Server health error: {ex.Message}");
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

        private ChatResponse? SendChatRequest(string serverUrl, string prompt)
        {
            try
            {
                var ctx = BlockReader.ExtractContext();
                LogSystemMessage("Extracted DWG context for AI request.");

                using var client = new AiServerClient(serverUrl);
                var history = _messages
                    .Where(m => m.Role == "user" || m.Role == "assistant" || m.Role == "system")
                    .Select(m => new ChatHistoryEntry(m.Role, m.Content))
                    .ToList();
                history.Add(new ChatHistoryEntry("user", prompt ?? string.Empty));

                return client.Chat(ctx, history);
            }
            catch (Exception ex)
            {
                MessageBox.Show($"Eroare la chat: {ex.Message}", "Eroare", MessageBoxButtons.OK, MessageBoxIcon.Error);
                return null;
            }
        }
    }
}
