# Trust the session's proxy CA bundle for edge-tts, which pins certifi's store.
import ssl
try:
    import edge_tts.communicate as _c
    _c._SSL_CTX = ssl.create_default_context(cafile="/root/.ccr/ca-bundle.crt")
except Exception:
    pass
