from rag import HealthcareRAG


def main() -> None:
    rag = HealthcareRAG()
    print(f"Indexed {rag.index_documents()} document chunks.")
    print("Healthcare Document Assistant. Type 'exit' to quit.")
    while True:
        question = input("\nQuestion: ").strip()
        if question.lower() == "exit":
            break
        print("\n" + rag.answer(question))


if __name__ == "__main__":
    main()
