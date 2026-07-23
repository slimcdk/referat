import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Observable } from 'rxjs';

@Injectable({
  providedIn: 'root'
})
export class MeetingService {
  private apiUrl = 'http://localhost:5000/api';
  private http = inject(HttpClient);

  getHeaders(): HttpHeaders {
    const token = localStorage.getItem('access_token');
    return token ? new HttpHeaders().set('Authorization', `Bearer ${token}`) : new HttpHeaders();
  }

  getMeetings(): Observable<any[]> {
    return this.http.get<any[]>(`${this.apiUrl}/meetings`, { headers: this.getHeaders() });
  }

  getMeeting(id: number): Observable<any> {
    return this.http.get<any>(`${this.apiUrl}/meetings/${id}`, { headers: this.getHeaders() });
  }

  createMeeting(title: string): Observable<any> {
    return this.http.post<any>(`${this.apiUrl}/meetings`, { title }, { headers: this.getHeaders() });
  }

  deleteMeeting(id: number): Observable<any> {
    return this.http.delete<any>(`${this.apiUrl}/meetings/${id}`, { headers: this.getHeaders() });
  }

  processClip(clipId: number): Observable<any> {
    return this.http.post<any>(`${this.apiUrl}/meetings/clips/${clipId}/process`, {}, { headers: this.getHeaders() });
  }

  aggregateMeeting(meetingId: number): Observable<any> {
    return this.http.post<any>(`${this.apiUrl}/meetings/${meetingId}/aggregate`, {}, { headers: this.getHeaders() });
  }

  // --- Standalone Clips Endpoints ---
  getAllClips(): Observable<any[]> {
    return this.http.get<any[]>(`${this.apiUrl}/meetings/clips/all`, { headers: this.getHeaders() });
  }

  assignClip(clipId: number, meetingId: number): Observable<any> {
    const formData = new FormData();
    formData.append('meeting_id', meetingId.toString());
    return this.http.patch<any>(`${this.apiUrl}/meetings/clips/${clipId}`, formData, { headers: this.getHeaders() });
  }

  deleteClip(clipId: number): Observable<any> {
    return this.http.delete<any>(`${this.apiUrl}/meetings/clips/${clipId}`, { headers: this.getHeaders() });
  }

  semanticSearch(query: string, limit: number = 10): Observable<any[]> {
    return this.http.post<any[]>(`${this.apiUrl}/search`, { query, limit }, { headers: this.getHeaders() });
  }

  getSettings(): Observable<any> {
    return this.http.get<any>(`${this.apiUrl}/settings`, { headers: this.getHeaders() });
  }

  updateSettings(settings: any): Observable<any> {
    return this.http.put<any>(`${this.apiUrl}/settings`, settings, { headers: this.getHeaders() });
  }
}
