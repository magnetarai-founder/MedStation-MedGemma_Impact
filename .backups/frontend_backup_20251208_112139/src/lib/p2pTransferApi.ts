export interface InitRequest {
  filename: string
  size_bytes: number
  mime_type?: string
}

export interface InitResponse {
  transfer_id: string
  chunk_size: number
}

export async function initTransfer(body: InitRequest, signal?: AbortSignal): Promise<InitResponse> {
  const res = await fetch('/api/v1/p2p/transfer/init', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
    signal,
  })
  if (!res.ok) throw new Error((await res.text()) || 'Failed to init transfer')
  return res.json()
}

export async function uploadChunk(
  transferId: string,
  index: number,
  checksum: string,
  data: Blob,
  signal?: AbortSignal
): Promise<void> {
  const form = new FormData()
  form.append('transfer_id', transferId)
  form.append('index', String(index))
  form.append('checksum', checksum)
  form.append('chunk', data, `chunk_${index}`)

  const res = await fetch('/api/v1/p2p/transfer/upload-chunk', {
    method: 'POST',
    body: form,
    signal,
  })
  if (!res.ok) throw new Error((await res.text()) || 'Chunk upload failed')
}

export interface CommitRequest {
  transfer_id: string
  expected_sha256?: string
}

export async function commitTransfer(body: CommitRequest, signal?: AbortSignal): Promise<void> {
  const res = await fetch('/api/v1/p2p/transfer/commit', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
    signal,
  })
  if (!res.ok) throw new Error((await res.text()) || 'Commit failed')
}

export interface TransferStatus {
  received_indices?: number[]
  missing_indices?: number[]
  total_chunks?: number
  bytes_received?: number
}

export async function getTransferStatus(transferId: string, signal?: AbortSignal): Promise<TransferStatus> {
  const res = await fetch(`/api/v1/p2p/transfer/status/${transferId}`, { signal })
  if (!res.ok) throw new Error((await res.text()) || 'Status fetch failed')
  return res.json()
}

