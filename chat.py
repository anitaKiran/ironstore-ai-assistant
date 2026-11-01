from src.assistant import KnowledgeAssistant


def main() -> None:
    print("IronStore Enterprise AI Assistant")
    print("Ask questions about the company documents.")
    print("Commands: /clear to reset the conversation, /exit to quit.")

    try:
        assistant = KnowledgeAssistant()
    except Exception as exc:
        print(f"\nCould not start the assistant: {exc}")
        return

    # Stored only in memory for this terminal session.
    history = []

    while True:
        try:
            question = input("\nYou: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nGoodbye!")
            break

        if question.lower() == "/exit":
            print("Goodbye!")
            break

        if question.lower() == "/clear":
            history.clear()
            print("Conversation cleared.")
            continue

        if not question:
            continue

        print("\nSearching documents and preparing an answer...")

        try:
            result = assistant.ask_question(question, history)
        except Exception as exc:
            print(f"\nThe request failed: {exc}")
            print("You can try again.")
            continue

        print(f"\nAssistant:\n{result['answer']}")

        if result["sources"]:
            print("\nSources:")

            for source in result["sources"]:
                print(
                    f"[{source['label']}] {source['source']} "
                    f"— PDF page {source['page']}"
                )

        history.extend(
            [
                {"role": "user", "content": question},
                {"role": "assistant", "content": result["answer"]},
            ]
        )

        # Keep the terminal session's stored history small.
        history = history[-6:]


if __name__ == "__main__":
    main()