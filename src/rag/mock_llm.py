class MockLLM:
    """A mock Language Model for deterministic responses as required by the capstone.

    For grounded generation, this mock LLM will primarily rely on the retrieved context
    and a similarity threshold to decide if it can provide an answer or trigger an
    'I don't know' fallback.
    """

    def __init__(self, name="mock-llm-v1", similarity_threshold=0.1):
        self.name = name
        self.similarity_threshold = similarity_threshold

    def generate_content(self, prompt, retrieved_context=None, retrieval_score=None):
        """
        Generates a response based on the prompt and optionally retrieved context.
        For evaluation, this method will simulate grounded generation.

        Args:
            prompt (str): The user's query.
            retrieved_context (list[str]): A list of retrieved text chunks.
            retrieval_score (float): The highest similarity score of the retrieved chunks.

        Returns:
            str: A simulated response or an 'I don't know' message.
        """
        if retrieved_context and retrieval_score is not None:
            # In a real scenario, the prompt and context would be fed to an actual LLM.
            # For MOCK_LLM, we simulate grounding based on retrieval_score.
            if retrieval_score >= self.similarity_threshold:
                # Simulate an answer based on context, potentially by concatenating
                # or summarizing the context (simplistic for mock).
                context_str = " ".join(retrieved_context)
                return f"Based on the information provided: {context_str[:200]}... (Simulated answer for: {prompt[:50]}...)"
            else:
                return "I don't know, the information provided is not sufficient or relevant enough to answer your question."
        else:
            # If no context is provided, or for general non-grounded prompts
            return f"Mock LLM received prompt: {prompt[:100]}... (No specific context provided for grounding.)"

# Initialize the mock LLM with a default similarity threshold (this will be calibrated in Task 4)
mock_llm = MockLLM()
print(f"Mock LLM '{mock_llm.name}' initialized with a similarity threshold of {mock_llm.similarity_threshold}.")