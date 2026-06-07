import { useRef, useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../../api/client'

const ALLOWED = ['.jpg', '.jpeg', '.tif', '.tiff']

function fmtBytes(n: number) {
  return n < 1024 * 1024 ? `${(n / 1024).toFixed(0)} KB` : `${(n / 1024 / 1024).toFixed(1)} MB`
}

export default function FlightUpload({ flightId }: { flightId: string }) {
  const qc = useQueryClient()
  const inputRef = useRef<HTMLInputElement>(null)
  const [files, setFiles] = useState<File[]>([])
  const [progress, setProgress] = useState(0)
  const [uploaded, setUploaded] = useState(false)
  const [dragOver, setDragOver] = useState(false)
  const [conflictMsg, setConflictMsg] = useState('')

  const uploadMutation = useMutation({
    mutationFn: async () => {
      const form = new FormData()
      files.forEach((f) => form.append('files', f))
      await api.post(`/flights/${flightId}/upload`, form, {
        onUploadProgress: (e) => setProgress(Math.round((e.loaded / (e.total ?? 1)) * 100)),
      })
      setUploaded(true)
    },
  })

  const processMutation = useMutation({
    mutationFn: () => api.post(`/flights/${flightId}/process`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['flight', flightId] })
      qc.invalidateQueries({ queryKey: ['flight-status', flightId] })
    },
    onError: (err: any) => {
      if (err.response?.status === 409) setConflictMsg('Обробка вже запущена')
    },
  })

  const addFiles = (incoming: FileList | null) => {
    if (!incoming) return
    const valid = Array.from(incoming).filter((f) =>
      ALLOWED.some((ext) => f.name.toLowerCase().endsWith(ext)),
    )
    setFiles((prev) => [...prev, ...valid])
  }

  return (
    <div>
      <div
        className={`upload-zone ${dragOver ? 'drag-over' : ''}`}
        onClick={() => inputRef.current?.click()}
        onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
        onDragLeave={() => setDragOver(false)}
        onDrop={(e) => { e.preventDefault(); setDragOver(false); addFiles(e.dataTransfer.files) }}
      >
        Перетягніть або клікніть для вибору знімків<br />
        <small>(.jpg, .jpeg, .tif, .tiff)</small>
        <input
          ref={inputRef}
          type="file"
          multiple
          accept=".jpg,.jpeg,.tif,.tiff"
          style={{ display: 'none' }}
          onChange={(e) => addFiles(e.target.files)}
        />
      </div>

      {files.length > 0 && (
        <div className="file-list">
          {files.map((f, i) => (
            <div key={i} className="file-item">
              <span>{f.name}</span>
              <span>{fmtBytes(f.size)}</span>
            </div>
          ))}
        </div>
      )}

      {uploadMutation.isPending && (
        <div className="progress-bar">
          <div className="progress-bar-fill" style={{ width: `${progress}%` }} />
        </div>
      )}

      {!uploaded && (
        <button
          className="btn btn-primary"
          style={{ marginTop: 8 }}
          disabled={files.length < 3 || uploadMutation.isPending}
          onClick={() => uploadMutation.mutate()}
        >
          Завантажити ({files.length} файлів)
        </button>
      )}

      {uploaded && (
        <>
          {conflictMsg && <div style={{ color: '#f44336', fontSize: 13 }}>{conflictMsg}</div>}
          <button
            className="btn btn-primary"
            style={{ marginTop: 8 }}
            disabled={processMutation.isPending}
            onClick={() => processMutation.mutate()}
          >
            Запустити обробку
          </button>
        </>
      )}
    </div>
  )
}
