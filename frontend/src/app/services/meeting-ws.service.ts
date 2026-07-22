import { Injectable } from '@angular/core';
import { webSocket, WebSocketSubject } from 'rxjs/webSocket';
import { Observable } from 'rxjs';

@Injectable({
  providedIn: 'root'
})
export class MeetingWsService {
  private wsUrl = 'ws://localhost:5000/api/ws/meetings';

  connectToMeetingProgress(meetingId: number): Observable<any> {
    const socket$: WebSocketSubject<any> = webSocket(`${this.wsUrl}/${meetingId}`);
    return socket$.asObservable();
  }
}
