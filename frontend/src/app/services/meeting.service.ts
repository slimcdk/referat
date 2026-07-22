import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

@Injectable({
  providedIn: 'root'
})
export class MeetingService {
  private apiUrl = 'http://localhost:5000/api';

  constructor(private http: HttpClient) {}

  getMeetings(): Observable<any[]> {
    return this.http.get<any[]>(`${this.apiUrl}/meetings`);
  }

  getMeeting(id: number): Observable<any> {
    return this.http.get<any>(`${this.apiUrl}/meetings/${id}`);
  }

  semanticSearch(query: string, limit: number = 10): Observable<any[]> {
    return this.http.post<any[]>(`${this.apiUrl}/search`, { query, limit });
  }

  getSettings(): Observable<any> {
    return this.http.get<any>(`${this.apiUrl}/settings`);
  }

  updateSettings(settings: any): Observable<any> {
    return this.http.put<any>(`${this.apiUrl}/settings`, settings);
  }
}
