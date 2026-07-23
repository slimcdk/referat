import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Observable, from } from 'rxjs';
import { concatMap, last, map } from 'rxjs/operators';

@Injectable({
  providedIn: 'root'
})
export class MeetingUploadService {
  private apiUrl = 'http://localhost:5000/api/meetings';
  private http = inject(HttpClient);

  private getHeaders(): HttpHeaders {
    const token = localStorage.getItem('access_token');
    return token ? new HttpHeaders().set('Authorization', `Bearer ${token}`) : new HttpHeaders();
  }

  uploadFileInChunks(meetingId: number | null, file: File): Observable<any> {
    const chunkSize = 5 * 1024 * 1024; // 5MB chunks
    const totalChunks = Math.ceil(file.size / chunkSize);
    const uploadId = crypto.randomUUID();

    const chunkUploads = [];

    for (let i = 0; i < totalChunks; i++) {
      const start = i * chunkSize;
      const end = Math.min(start + chunkSize, file.size);
      const chunk = file.slice(start, end);

      const formData = new FormData();
      formData.append('upload_id', uploadId);
      formData.append('chunk_index', i.toString());
      formData.append('file', chunk, `${file.name}.part_${i}`);

      chunkUploads.push({ formData, index: i });
    }

    let uploadedCount = 0;
    return from(chunkUploads).pipe(
      concatMap(item => {
        return this.http.post(`${this.apiUrl}/upload/chunk`, item.formData, { headers: this.getHeaders() }).pipe(
          map(() => {
            uploadedCount++;
            const progress = Math.round((uploadedCount / totalChunks) * 100);
            return { type: 'progress', progress, chunkIndex: item.index };
          })
        );
      }),
      last(),
      concatMap(() => {
        const completeData = new FormData();
        completeData.append('upload_id', uploadId);
        completeData.append('filename', file.name);
        completeData.append('total_chunks', totalChunks.toString());

        const url = meetingId 
          ? `${this.apiUrl}/${meetingId}/clips/upload/complete` 
          : `${this.apiUrl}/clips/upload/complete`;

        return this.http.post(url, completeData, { headers: this.getHeaders() }).pipe(
          map(response => {
            return { type: 'complete', data: response };
          })
        );
      })
    );
  }

  // 1. Upload a single recording chunk on-the-fly as it is recorded in the browser
  uploadSingleChunk(uploadId: string, chunkIndex: number, chunk: Blob, filename: string): Observable<any> {
    const formData = new FormData();
    formData.append('upload_id', uploadId);
    formData.append('chunk_index', chunkIndex.toString());
    formData.append('file', chunk, `${filename}.part_${chunkIndex}`);

    return this.http.post(`${this.apiUrl}/upload/chunk`, formData, { headers: this.getHeaders() });
  }

  // 2. Finalize recording chunks (optionally under a specific meeting, or standalone)
  completeRecordingUpload(meetingId: number | null, uploadId: string, filename: string, totalChunks: number): Observable<any> {
    const completeData = new FormData();
    completeData.append('upload_id', uploadId);
    completeData.append('filename', filename);
    completeData.append('total_chunks', totalChunks.toString());

    const url = meetingId 
      ? `${this.apiUrl}/${meetingId}/clips/upload/complete` 
      : `${this.apiUrl}/clips/upload/complete`;

    return this.http.post(url, completeData, { headers: this.getHeaders() });
  }
}
