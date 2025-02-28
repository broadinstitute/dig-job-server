import zlib

class LogCompressor:
    @staticmethod
    def compress(log_content):
        return zlib.compress(log_content.encode('utf-8'))

    @staticmethod
    def decompress(compressed_log):
        try:
            return zlib.decompress(compressed_log).decode('utf-8')
        except Exception as e:
            print(f"Decompression error: {e}")
            return ""
