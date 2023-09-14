from langchain.text_splitter import RecursiveCharacterTextSplitter


class DocumentChunker:
    def __init__(self, chunk_size: int, chunk_overlap: int, length_function=len):
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=length_function,
        )

    def chunk(self, text: str):
        return [
            doc.page_content
            for doc in self.text_splitter.create_documents(texts=[text])
        ]
