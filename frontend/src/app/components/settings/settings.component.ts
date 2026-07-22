import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatCardModule } from '@angular/material/card';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatSelectModule } from '@angular/material/select';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MeetingService } from '../../services/meeting.service';

@Component({
  selector: 'app-settings',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatCardModule,
    MatFormFieldModule,
    MatSelectModule,
    MatInputModule,
    MatButtonModule,
    MatIconModule
  ],
  templateUrl: './settings.component.html',
  styleUrl: './settings.component.scss'
})
export class SettingsComponent implements OnInit {
  llm_size: string = 'small';
  data_retention_days: number = 30;
  isSaving: boolean = false;
  statusMessage: string = '';

  constructor(private meetingService: MeetingService) {}

  ngOnInit(): void {
    this.meetingService.getSettings().subscribe({
      next: (data) => {
        this.llm_size = data.llm_size;
        this.data_retention_days = data.data_retention_days;
      },
      error: (err) => console.error('Failed to load settings', err)
    });
  }

  saveSettings(): void {
    this.isSaving = true;
    this.statusMessage = 'Saving settings...';
    
    const settings = {
      llm_size: this.llm_size,
      data_retention_days: this.data_retention_days
    };

    this.meetingService.updateSettings(settings).subscribe({
      next: () => {
        this.isSaving = false;
        this.statusMessage = 'Settings saved successfully!';
      },
      error: (err) => {
        console.error('Failed to save settings', err);
        this.statusMessage = 'Failed to save settings.';
        this.isSaving = false;
      }
    });
  }
}
