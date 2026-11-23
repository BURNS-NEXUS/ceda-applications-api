from django.core.files.base import ContentFile
from django.core.files.storage import Storage
from vercel.blob import BlobNotFoundError
from vercel.blob import sync as blob


class PrivateDocumentStorage(Storage):
    def _save(self, name, content):
        return blob.put_blob(name, content.read(), access="private").pathname

    def _open(self, name, mode="rb"):
        try:
            return ContentFile(blob.get_blob(name, access="private").body, name=name)
        except BlobNotFoundError as exc:
            raise FileNotFoundError(name) from exc

    def exists(self, name):
        try:
            blob.head_blob(name)
        except BlobNotFoundError:
            return False
        return True

    def delete(self, name):
        blob.delete_blob(name)

    def size(self, name):
        return blob.head_blob(name).size
