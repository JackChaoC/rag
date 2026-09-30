from rag.services.splitting.markdown_node_parser import MarkdownNodeParser


class SplitterService:
    def __init__(self, markdownNodeParser: MarkdownNodeParser):
        self.markdownNodeParser = markdownNodeParser

    def split(self, documents):
        return self.markdownNodeParser.get_nodes_from_documents(documents)
