
class PromptTokenBudget:

    def __init__(
        self,
        ollama_client,
        output_reserve: int = 2048,
        safety_margin: int = 512
    ):
        self.ollama_client = ollama_client
        self.context_size = ollama_client.num_ctx
        self.output_reserve = output_reserve
        self.safety_margin = safety_margin

    @property
    def max_input_tokens(self):
        return (
            self.context_size
            - self.output_reserve
            - self.safety_margin
        )

    def validate(self, prompt: str) -> dict:
        """
        Validación preliminar basada en caracteres.
        El conteo real se obtiene durante la inferencia.
        """

        estimated_chars = len(prompt)

        return {
            "estimated_characters": estimated_chars,
            "context_size": self.context_size,
            "output_reserve": self.output_reserve,
            "safety_margin": self.safety_margin,
            "max_input_tokens": self.max_input_tokens,
            "requires_runtime_validation": True
        }

    def validate_actual_tokens(
        self,
        prompt_tokens: int
    ) -> dict:

        return {
            "prompt_tokens": prompt_tokens,
            "context_size": self.context_size,
            "output_reserve": self.output_reserve,
            "safety_margin": self.safety_margin,
            "max_input_tokens": self.max_input_tokens,
            "fits": (
                prompt_tokens <= self.max_input_tokens
            ),
            "remaining_input_budget": (
                self.max_input_tokens - prompt_tokens
            )
        }
