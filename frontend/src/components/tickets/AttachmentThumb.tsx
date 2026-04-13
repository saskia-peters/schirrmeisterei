/**
 * AttachmentThumb
 *
 * Fetches an attachment via the authenticated API client (which adds the
 * Authorization header) and renders a thumbnail + download link. This is
 * necessary because the download endpoint requires authentication — a plain
 * <img src> or <a href> would not send the Bearer token (A-5 fix).
 *
 * Images are rendered as inline thumbnails. PDFs show a document icon.
 */
import { useEffect, useState } from 'react'
import { apiClient } from '@/api/client'
import type { Attachment } from '@/types'

interface AttachmentThumbProps {
  attachment: Attachment
  onDelete?: (id: string) => void
  canDelete?: boolean
}

export function AttachmentThumb({ attachment, onDelete, canDelete }: AttachmentThumbProps) {
  const [blobUrl, setBlobUrl] = useState<string | null>(null)
  const [error, setError] = useState(false)
  const isPdf = attachment.content_type === 'application/pdf'

  useEffect(() => {
    let objectUrl = ''
    apiClient
      .get<Blob>(attachment.url, { responseType: 'blob' })
      .then((res) => {
        objectUrl = URL.createObjectURL(res.data)
        setBlobUrl(objectUrl)
      })
      .catch(() => setError(true))

    return () => {
      if (objectUrl) URL.revokeObjectURL(objectUrl)
    }
  }, [attachment.url])

  const handleDownload = () => {
    if (!blobUrl) return
    const a = document.createElement('a')
    a.href = blobUrl
    a.download = attachment.filename
    a.click()
  }

  return (
    <div className="attachment-thumbnail-wrap">
      <button
        type="button"
        className="attachment-thumbnail"
        title={`${attachment.filename} (${Math.round(attachment.file_size / 1024)} KB)`}
        onClick={handleDownload}
        disabled={!blobUrl && !error}
        aria-label={`Download ${attachment.filename}`}
      >
        {error ? (
          <span className="thumbnail-error">Failed to load</span>
        ) : blobUrl ? (
          isPdf ? (
            <span className="thumbnail-pdf-icon" aria-hidden>📄</span>
          ) : (
            <img src={blobUrl} alt={attachment.filename} className="thumbnail-img" />
          )
        ) : (
          <span className="thumbnail-loading">…</span>
        )}
        <span className="thumbnail-name">{attachment.filename}</span>
      </button>
      {canDelete && onDelete && (
        <button
          type="button"
          className="attachment-delete-btn"
          aria-label={`Remove ${attachment.filename}`}
          title="Remove attachment"
          onClick={() => onDelete(attachment.id)}
        >
          ✕
        </button>
      )}
    </div>
  )
}
