import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatCardModule } from '@angular/material/card';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatDividerModule } from '@angular/material/divider';
import { MeetingService } from '../../services/meeting.service';
import { MeetingUploadService } from '../../services/meeting-upload.service';

@Component({
  selector: 'app-upload',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatCardModule,
    MatFormFieldModule,
    MatInputModule,
    MatProgressBarModule,
    MatButtonModule,
    MatIconModule,
    MatDividerModule
  ],
  templateUrl: './upload.component.html',
  styleUrl: './upload.component.scss'
})
export class UploadComponent implements OnInit {
  // Use Angular Signals for asynchronously updated fields to notify Zoneless change detection
  meetings = signal<any[]>([]);
  isLoadingMeetings = signal<boolean>(false);
  isUploading = signal<boolean>(false);
  uploadProgress = signal<number>(0);
  uploadStatus = signal<string>('');

  showCreateForm: boolean = false;
  newMeetingTitle: string = '';
  selectedMeeting: any | null = null;
  selectedFile: File | null = null;

  constructor(
    private meetingService: MeetingService,
    private uploadService: MeetingUploadService
  ) {}

  ngOnInit(): void {
    this.loadMeetings();
  }

  loadMeetings(): void {
    this.isLoadingMeetings.set(true);
    this.meetingService.getMeetings().subscribe({
      next: (data) => {
        this.meetings.set(data);
        this.isLoadingMeetings.set(false);
        
        // Refresh selected meeting object if expanded to get updated clip statuses
        if (this.selectedMeeting) {
          const updated = this.meetings().find(m => m.id === this.selectedMeeting.id);
          if (updated) {
            this.selectedMeeting = updated;
          }
        }
      },
      error: (err) => {
        console.error('Failed to load meetings', err);
        this.isLoadingMeetings.set(false);
      }
    });
  }

  createMeeting(): void {
    if (!this.newMeetingTitle.trim()) return;

    this.meetingService.createMeeting(this.newMeetingTitle).subscribe({
      next: (data) => {
        this.newMeetingTitle = '';
        this.showCreateForm = false;
        this.loadMeetings();
      },
      error: (err) => {
        console.error('Failed to create meeting', err);
      }
    });
  }

  deleteMeeting(id: number, event: Event): void {
    event.stopPropagation(); // Avoid expanding the card row when clicking delete
    
    if (confirm('Er du sikker på, at du vil slette dette referat og alle tilhørende klip?')) {
      this.meetingService.deleteMeeting(id).subscribe({
        next: () => {
          if (this.selectedMeeting?.id === id) {
            this.selectedMeeting = null;
          }
          this.loadMeetings();
        },
        error: (err) => {
          console.error('Failed to delete meeting', err);
        }
      });
    }
  }

  selectMeeting(meeting: any): void {
    if (this.selectedMeeting?.id === meeting.id) {
      this.selectedMeeting = null;
    } else {
      this.selectedMeeting = meeting;
      this.selectedFile = null;
      this.isUploading.set(false);
      this.uploadProgress.set(0);
      this.uploadStatus.set('');
    }
  }

  onFileSelected(event: any): void {
    const file = event.target.files[0];
    if (file) {
      this.selectedFile = file;
    }
  }

  uploadClip(): void {
    if (!this.selectedMeeting || !this.selectedFile) return;

    this.isUploading.set(true);
    this.uploadProgress.set(0);
    this.uploadStatus.set('Uploader klip i bidder...');

    this.uploadService.uploadFileInChunks(this.selectedMeeting.id, this.selectedFile).subscribe({
      next: (event) => {
        if (event.type === 'progress') {
          this.uploadProgress.set(event.progress);
          this.uploadStatus.set(`Uploader: ${event.progress}%`);
        } else if (event.type === 'complete') {
          this.uploadProgress.set(100);
          this.uploadStatus.set('Færdiggør og samler fil...');
          console.log('Clip upload complete!', event.data);
          this.selectedFile = null;
          this.isUploading.set(false);
          this.loadMeetings(); // Reload to fetch the new clip in details list
        }
      },
      error: (err) => {
        console.error('Clip upload failed', err);
        this.uploadStatus.set('Upload fejlede. Prøv venligst igen.');
        this.isUploading.set(false);
      }
    });
  }

  processClip(clipId: number): void {
    this.meetingService.processClip(clipId).subscribe({
      next: () => {
        this.loadMeetings(); // Reload to show 'processing' status
      },
      error: (err) => {
        console.error('Failed to start clip processing', err);
      }
    });
  }

  aggregateMeeting(meetingId: number): void {
    this.meetingService.aggregateMeeting(meetingId).subscribe({
      next: () => {
        this.loadMeetings(); // Reload to show 'processing' status for meeting
      },
      error: (err) => {
        console.error('Failed to start meeting aggregation', err);
      }
    });
  }

  hasCompletedClips(meeting: any): boolean {
    if (!meeting.clips || meeting.clips.length === 0) return false;
    return meeting.clips.some((c: any) => c.status === 'completed');
  }

  formatStatus(statusStr: string): string {
    switch (statusStr) {
      case 'empty': return 'Tomt referat';
      case 'pending': return 'Klar til behandling';
      case 'processing': return 'Behandler...';
      case 'completed': return 'Færdigbehandlet';
      case 'failed': return 'Fejlet';
      case 'processing_clips': return 'Behandler klip...';
      case 'clip_processed': return 'Klip færdigbehandlet';
      default: return statusStr;
    }
  }
}
