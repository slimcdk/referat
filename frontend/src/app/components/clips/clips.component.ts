import { Component, OnInit, signal, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute } from '@angular/router';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatDividerModule } from '@angular/material/divider';
import { MatSelectModule } from '@angular/material/select';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MeetingService } from '../../services/meeting.service';
import { MeetingUploadService } from '../../services/meeting-upload.service';
import { AppButton } from '../button/button.component';

@Component({
  selector: 'app-clips',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatCardModule,
    MatButtonModule,
    MatIconModule,
    MatProgressBarModule,
    MatDividerModule,
    MatSelectModule,
    MatFormFieldModule,
    MatInputModule,
    AppButton
  ],
  templateUrl: './clips.component.html',
  styleUrl: './clips.component.scss'
})
export class ClipsComponent implements OnInit {
  private meetingService = inject(MeetingService);
  private uploadService = inject(MeetingUploadService);
  private route = inject(ActivatedRoute);

  // Use Angular Signals for asynchronously updated fields to notify Zoneless change detection
  clips = signal<any[]>([]);
  meetings = signal<any[]>([]);
  isLoadingClips = signal<boolean>(false);
  isUploading = signal<boolean>(false);
  uploadProgress = signal<number>(0);
  uploadStatus = signal<string>('');

  selectedFile: File | null = null;

  // Recording State & Properties
  isRecordingMode = signal<boolean>(false);
  isCurrentlyRecording = signal<boolean>(false);
  includeMic = true;

  audioContext: AudioContext | null = null;
  combinedStream: MediaStream | null = null;
  mediaRecorder: MediaRecorder | null = null;
  recordedChunksCount = 0;
  recordingUploadId = '';
  recordingDuration = 0;
  recordingInterval: any = null;

  ngOnInit(): void {
    this.loadData();
    this.handleGlobalActions();
  }

  handleGlobalActions(): void {
    this.route.queryParams.subscribe(params => {
      const action = params['action'];
      if (action === 'upload') {
        // Automatically open the file select dialog on global Upload click
        setTimeout(() => {
          const fileInput = document.querySelector('.clips-header input[type="file"]') as HTMLInputElement;
          if (fileInput) {
            fileInput.click();
          }
        }, 300);
      } else if (action === 'record') {
        // Automatically toggle the recording panel on global Record click
        setTimeout(() => {
          this.isRecordingMode.set(true);
        }, 100);
      }
    });
  }

  loadData(): void {
    this.isLoadingClips.set(true);
    
    // Fetch all clips
    this.meetingService.getAllClips().subscribe({
      next: (clipsData) => {
        this.clips.set(clipsData);
        this.isLoadingClips.set(false);
      },
      error: (err) => {
        console.error('Failed to load clips', err);
        this.isLoadingClips.set(false);
      }
    });

    // Fetch meetings (for assignment selection list)
    this.meetingService.getMeetings().subscribe({
      next: (meetingsData) => {
        this.meetings.set(meetingsData);
      },
      error: (err) => {
        console.error('Failed to load meetings', err);
      }
    });
  }

  onFileSelected(event: any): void {
    const file = event.target.files[0];
    if (file) {
      this.selectedFile = file;
    }
  }

  uploadStandaloneFile(): void {
    if (!this.selectedFile) return;

    this.isUploading.set(true);
    this.uploadProgress.set(0);
    this.uploadStatus.set('Uploader standalone klip...');

    // Upload with null meetingId (creates an unassigned clip)
    this.uploadService.uploadFileInChunks(null, this.selectedFile).subscribe({
      next: (event) => {
        if (event.type === 'progress') {
          this.uploadProgress.set(event.progress);
          this.uploadStatus.set(`Uploader: ${event.progress}%`);
        } else if (event.type === 'complete') {
          this.uploadProgress.set(100);
          this.uploadStatus.set('Samler fil på serveren...');
          console.log('Standalone upload complete!', event.data);
          this.selectedFile = null;
          this.isUploading.set(false);
          this.loadData(); // Reload list
        }
      },
      error: (err) => {
        console.error('Standalone upload failed', err);
        this.uploadStatus.set('Upload fejlede. Prøv venligst igen.');
        this.isUploading.set(false);
      }
    });
  }

  deleteClip(clipId: number): void {
    if (confirm('Er du sikker på, at du vil slette denne optagelse permanent fra disken?')) {
      this.meetingService.deleteClip(clipId).subscribe({
        next: () => {
          this.loadData();
        },
        error: (err) => {
          console.error('Failed to delete clip', err);
        }
      });
    }
  }

  processClip(clipId: number): void {
    this.meetingService.processClip(clipId).subscribe({
      next: () => {
        this.loadData(); // Show processing status
      },
      error: (err) => {
        console.error('Failed to process clip', err);
      }
    });
  }

  assignClip(clipId: number, meetingId: number): void {
    this.meetingService.assignClip(clipId, meetingId).subscribe({
      next: () => {
        console.log(`Clip ${clipId} assigned to meeting ${meetingId}.`);
        this.loadData(); // Reload to show assigned section
      },
      error: (err) => {
        console.error('Failed to assign clip', err);
      }
    });
  }

  createMeetingForClip(clipId: number): void {
    const title = prompt('Indtast titlen for det nye referat:');
    if (!title || !title.trim()) return;

    // 1. Create meeting
    this.meetingService.createMeeting(title).subscribe({
      next: (meeting) => {
        console.log('Meeting created successfully!', meeting);
        // 2. Assign clip to it
        this.assignClip(clipId, meeting.id);
      },
      error: (err) => {
        console.error('Failed to create meeting for clip', err);
      }
    });
  }

  getUnassignedClips(): any[] {
    return this.clips().filter(c => !c.meeting_id);
  }

  getAssignedClips(): any[] {
    return this.clips().filter(c => c.meeting_id);
  }

  getMeetingTitle(meetingId: number): string {
    const meet = this.meetings().find(m => m.id === meetingId);
    return meet ? meet.title : `Referat ID ${meetingId}`;
  }

  formatStatus(statusStr: string): string {
    switch (statusStr) {
      case 'pending': return 'Klar til behandling';
      case 'processing': return 'Behandler...';
      case 'completed': return 'Færdigbehandlet';
      case 'failed': return 'Fejlet';
      default: return statusStr;
    }
  }

  // --- Browser Recording Logic (Decoupled/Standalone) ---
  async startBrowserRecording(): Promise<void> {
    this.recordedChunksCount = 0;
    this.recordingDuration = 0;
    this.recordingUploadId = crypto.randomUUID();

    try {
      console.log("Requesting screen display media with system audio...");
      const screenStream = await navigator.mediaDevices.getDisplayMedia({
        video: true,
        audio: true
      });

      let mixedAudioStream: MediaStream | null = null;

      if (this.includeMic) {
        try {
          console.log("Requesting local microphone audio...");
          const micStream = await navigator.mediaDevices.getUserMedia({ audio: true });
          
          console.log("Initializing Web Audio API for mixing tracks...");
          this.audioContext = new (window.AudioContext || (window as any).webkitAudioContext)();
          const dest = this.audioContext.createMediaStreamDestination();

          if (screenStream.getAudioTracks().length > 0) {
            const screenSource = this.audioContext.createMediaStreamSource(new MediaStream([screenStream.getAudioTracks()[0]]));
            screenSource.connect(dest);
          }

          const micSource = this.audioContext.createMediaStreamSource(micStream);
          micSource.connect(dest);

          mixedAudioStream = dest.stream;
        } catch (micErr) {
          console.warn("Mikrofonadgang nægtet eller ikke tilgængelig. Optager kun systemlyd.", micErr);
        }
      }

      const videoTrack = screenStream.getVideoTracks()[0];
      const audioTrack = mixedAudioStream ? mixedAudioStream.getAudioTracks()[0] : (screenStream.getAudioTracks()[0] || null);

      const tracks = [videoTrack];
      if (audioTrack) {
        tracks.push(audioTrack);
      }

      this.combinedStream = new MediaStream(tracks);

      const options = { mimeType: 'video/webm; codecs=vp8,opus' };
      this.mediaRecorder = new MediaRecorder(this.combinedStream, options);

      this.isCurrentlyRecording.set(true);
      this.uploadStatus.set('Optager skærm og lyd...');
      this.uploadProgress.set(0);

      this.mediaRecorder.ondataavailable = (event) => {
        if (event.data && event.data.size > 0) {
          this.uploadRecordingChunk(event.data, this.recordedChunksCount);
          this.recordedChunksCount++;
        }
      };

      this.mediaRecorder.start(10000);

      this.recordingInterval = setInterval(() => {
        this.recordingDuration++;
      }, 1000);

      videoTrack.onended = () => {
        this.stopBrowserRecording();
      };

    } catch (err) {
      console.error("Kunne ikke starte browseroptagelse:", err);
      alert("Browseroptagelse blev afbrudt, eller der blev ikke givet tilladelse.");
      this.isCurrentlyRecording.set(false);
    }
  }

  stopBrowserRecording(): void {
    if (!this.isCurrentlyRecording()) return;

    console.log("Stopping browser recording...");
    this.isCurrentlyRecording.set(false);

    if (this.recordingInterval) {
      clearInterval(this.recordingInterval);
    }

    if (this.mediaRecorder && this.mediaRecorder.state !== 'inactive') {
      this.mediaRecorder.stop();
    }

    if (this.combinedStream) {
      this.combinedStream.getTracks().forEach(track => track.stop());
    }

    if (this.audioContext && this.audioContext.state !== 'closed') {
      this.audioContext.close();
    }

    this.uploadStatus.set('Afslutter optagelse og samler fil...');
    this.isUploading.set(true);
    this.uploadProgress.set(100);

    setTimeout(() => {
      const filename = `Optagelse_${new Date().toISOString().slice(0,10)}_${new Date().toTimeString().slice(0,8).replace(/:/g,'-')}.webm`;
      
      // Finalize with null meetingId (creates an unassigned clip)
      this.uploadService.completeRecordingUpload(
        null, 
        this.recordingUploadId, 
        filename, 
        this.recordedChunksCount
      ).subscribe({
        next: (res) => {
          console.log('Standalone recording finalize complete!', res);
          this.isUploading.set(false);
          this.uploadStatus.set('Optagelse gemt med succes!');
          this.isRecordingMode.set(false);
          this.loadData(); // Reload list
        },
        error: (err) => {
          console.error('Failed to finalize recording upload:', err);
          this.uploadStatus.set('Optagelse gemt, men oprettelse fejlede.');
          this.isUploading.set(false);
        }
      });
    }, 1500);
  }

  uploadRecordingChunk(chunk: Blob, index: number): void {
    const filename = `Optagelse_${new Date().toISOString().slice(0,10)}.webm`;
    this.uploadService.uploadSingleChunk(this.recordingUploadId, index, chunk, filename).subscribe({
      next: () => {
        console.log(`Uploaded standalone recording chunk ${index} successfully.`);
      },
      error: (err) => {
        console.error(`Failed to upload standalone recording chunk ${index}:`, err);
      }
    });
  }

  formatRecordingDuration(): string {
    const mins = Math.floor(this.recordingDuration / 60);
    const secs = this.recordingDuration % 60;
    return `${mins < 10 ? '0' : ''}${mins}:${secs < 10 ? '0' : ''}${secs}`;
  }
}
