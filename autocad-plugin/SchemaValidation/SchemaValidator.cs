using System;
using System.Collections.Generic;
using System.IO;
using Newtonsoft.Json.Linq;
using Newtonsoft.Json.Schema;

namespace AutocadAiAgent.SchemaValidation
{
    public sealed class SchemaValidator
    {
        private readonly string _schemaDirectory;

        public SchemaValidator(string schemaDirectory)
        {
            if (string.IsNullOrWhiteSpace(schemaDirectory))
            {
                throw new ArgumentException("Schema directory must be provided.", nameof(schemaDirectory));
            }

            _schemaDirectory = schemaDirectory;
        }

        public ValidationResult ValidateDwgContext(string jsonPayload)
        {
            return ValidateAgainstSchema(jsonPayload, "dwg-context.schema.json");
        }

        public ValidationResult ValidateActionPlan(string jsonPayload)
        {
            return ValidateAgainstSchema(jsonPayload, "action-plan.schema.json");
        }

        private ValidationResult ValidateAgainstSchema(string jsonPayload, string schemaFile)
        {
            if (string.IsNullOrWhiteSpace(jsonPayload))
            {
                return new ValidationResult(new[] { "Payload is empty." });
            }

            var schemaPath = Path.Combine(_schemaDirectory, schemaFile);
            if (!File.Exists(schemaPath))
            {
                return new ValidationResult(new[] { $"Schema file not found: {schemaPath}" });
            }

            var schema = JSchema.Parse(File.ReadAllText(schemaPath));
            var token = JToken.Parse(jsonPayload);

            IList<string> errors;
            var isValid = token.IsValid(schema, out errors);

            if (isValid)
            {
                return new ValidationResult(Array.Empty<string>());
            }

            return new ValidationResult(errors);
        }
    }
}
