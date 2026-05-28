using System.Collections.Generic;
using System.Linq;

namespace AutocadAiAgent.SchemaValidation
{
    public sealed class ValidationResult
    {
        public ValidationResult(IEnumerable<string> errors)
        {
            Errors = errors?.ToList() ?? new List<string>();
        }

        public bool IsValid => Errors.Count == 0;

        public IReadOnlyList<string> Errors { get; }
    }
}
