from src.agent.agent import MEMORY_FILE,run_agent
from src.memory.conversation import ConversationMemory
import uuid

thread_id = str(uuid.uuid4())


def main() -> None:
    """Run the terminal-based multi-turn application."""

    print("=" * 60)
    print("        CARTMIND - CUSTOMER SUPPORT AGENT")
    print("=" * 60)

    print("\nPersistent JSON conversation memory enabled.")

    # ---------------------------------------------------------
    # Create memory manager
    # ---------------------------------------------------------

    con_memory = ConversationMemory(MEMORY_FILE)

    # ---------------------------------------------------------
    # Ask for conversation ID
    # ---------------------------------------------------------

    conversation_id = input(
        "\nEnter conversation ID "
        "(e.g. customer-001): "
    ).strip()

    if not conversation_id:
        print("Conversation ID cannot be empty.")
        return

    # ---------------------------------------------------------
    # Load previous memory
    # ---------------------------------------------------------

    history = con_memory.get_history(conversation_id)

    if history:
        #print_history(history)

        print(
            f"\n[Memory] Loaded {len(history)} "
            f"previous messages."
        )

    else:
        print(
            "\n[Memory] Fresh conversation."
        )

    print("\nType 'exit' to end the conversation.")
    print("Type 'history' to display persisted memory.")
    print("Type 'clear' to delete this conversation.")
    print("-" * 60)

    # ---------------------------------------------------------
    # Multi-turn conversation loop
    # ---------------------------------------------------------

    while True:

        try:
            query = input("\nYou: ").strip()

        except (KeyboardInterrupt, EOFError):
            print("\n\nConversation ended.")
            break

        # -----------------------------------------------------
        # Exit
        # -----------------------------------------------------

        if query.lower() in {"exit", "quit", "q"}:
            print("\nConversation ended.")
            break

        # -----------------------------------------------------
        # Show history
        # -----------------------------------------------------

        if query.lower() == "history":

            history = con_memory.get_history(conversation_id)

            #print_history(history)

            continue

        # -----------------------------------------------------
        # Clear conversation
        # -----------------------------------------------------

        if query.lower() == "clear":

            con_memory.clear(conversation_id)

            print(
                "\n[Memory] Conversation history "
                "has been cleared."
            )

            continue

        # -----------------------------------------------------
        # Ignore empty messages
        # -----------------------------------------------------

        if not query:
            print("Please enter a message.")
            continue

        # -----------------------------------------------------
        # Run agent
        # -----------------------------------------------------

        

        answer = run_agent(
                query=query,
                conversation_id=conversation_id,
                con_memory=con_memory,
                thread_id=thread_id
            )

        print(f"\nAgent: {answer}")



if __name__ == "__main__":
    main()
