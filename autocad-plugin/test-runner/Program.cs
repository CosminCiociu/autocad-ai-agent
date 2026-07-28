using System;
using System.IO;
using AutoCADPlugin;

Console.WriteLine("Starting AiExecute test runner...");

var planPath = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "..", "..", "..", "sample_action_plan.json");
var reportPath = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "..", "..", "..", "execution_report_test.json");

Console.WriteLine($"Plan path: {planPath}");
Console.WriteLine($"Report path: {reportPath}");

var exitCode = Commands.AiExecute(planPath, null, previewOnly: true, reportPath: reportPath);
Console.WriteLine($"AiExecute returned exit code {exitCode}");
