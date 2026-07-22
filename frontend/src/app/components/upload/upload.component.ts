import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatCardModule } from '@angular/material/card';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
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
    MatIconModule
  ],
  templateUrl: './upload.component.html',
  styleUrl: './upload.component.scss'
})
export class UploadComponent {
  title: string = '';
  selectedFile: File | null = null;
  isUploading: boolean = false;
  uploadProgress: number = 0;
  uploadStatus: string = '';

  constructor(private uploadService: MeetingUploadService) {}

  onFileSelected(event: any): void {
    const file = event.target.files[0];
    if (file) {
      this.selectedFile = file;
      if (!this.title) {
        const dotIdx = file.name.lastIndexOf('.');
        this.title = dotIdx > 0 ? file.name.substring(0, dotIdx) : file.name;
      }
    }
  }

  startUpload(): void {
    if (!this.selectedFile || !this.title) return;

    this.isUploading = true;
    this.uploadProgress = 0;
    this.uploadStatus = 'Uploading chunks...';

    this.uploadService.uploadFileInChunks(this.selectedFile, this.title).subscribe({
      next: (event) => {
        if (event.type === 'progress') {
          this.uploadProgress = event.progress;
          this.uploadStatus = `Uploading: ${event.progress}%`;
        } else if (event.type === 'complete') {
          this.uploadProgress = 100;
          this.uploadStatus = 'Processing and merging file...';
          console.log('Upload complete!', event.data);
          this.resetForm();
        }
      },
      error: (err) => {
        console.error('Upload failed', err);
        this.uploadStatus = 'Upload failed. Please try again.';
        this.isUploading = false;
      }
    });
  }

  private resetForm(): void {
    this.title = '';
    this.selectedFile = null;
    this.isUploading = false;
    this.uploadProgress = 0;
    this.uploadStatus = 'Upload successful!';
  }
}
