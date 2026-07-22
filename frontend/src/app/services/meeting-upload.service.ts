import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, from } from 'rxjs';
import { concatMap, last, map } from 'rxjs/operators';

@Injectable({
  providedIn: 'root'
})
export class MeetingUploadService {
  private apiUrl = 'http://localhost:5000/api/meetings';

  constructor(private http: HttpClient) {}

  uploadFileInChunks(file: File, title: string): Observable<any> {
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
        return this.http.post(`${this.apiUrl}/upload/chunk`, item.formData).pipe(
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
        completeData.append('title', title);
        completeData.append('filename', file.name);
        completeData.append('total_chunks', totalChunks.toString());

        return this.http.post(`${this.apiUrl}/upload/complete`, completeData).pipe(
          map(response => {
            return { type: 'complete', data: response };
          })
        );
      })
    );
  }
}
