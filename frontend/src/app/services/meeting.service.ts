import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Observable } from 'rxjs';

@Injectable({
  providedIn: 'root'
})
export class MeetingService {
  private apiUrl = 'http://localhost:5000/api';

  constructor(private http: HttpClient) {}

  private getHeaders(): HttpHeaders {
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
