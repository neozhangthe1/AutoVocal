def resolve_encoding(s):
    if type(s) is str:
        s = bytes([ord(c) for c in s])
    return bytes([ord(c) for c in s.decode("utf-8")]).decode("gbk")

