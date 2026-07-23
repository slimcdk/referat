import { Component, OnInit, signal, inject } from '@angular/core';
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
  private meetingService = inject(MeetingService);

  // Use modern Angular Signals to ensure perfect compatibility with Zoneless change detection
  llm_size = signal<string>('small');
  data_retention_days = signal<number>(30);
  isSaving = signal<boolean>(false);
  statusMessage = signal<string>('');

  ngOnInit(): void {
    this.meetingService.getSettings().subscribe({
      next: (data) => {
        this.llm_size.set(data.llm_size);
        this.data_retention_days.set(data.data_retention_days);
      },
      error: (err) => console.error('Failed to load settings', err)
    });
  }

  saveSettings(): void {
    this.isSaving.set(true);
    this.statusMessage.set('Gemmer indstillinger...');
    
    const settings = {
      llm_size: this.llm_size(),
      data_retention_days: this.data_retention_days()
    };

    this.meetingService.updateSettings(settings).subscribe({
      next: () => {
        this.isSaving.set(false);
        this.statusMessage.set('Indstillingerne blev gemt med succes!');
      },
      error: (err) => {
        console.error('Failed to save settings', err);
        this.statusMessage.set('Kunne ikke gemme indstillingerne.');
        this.isSaving.set(false);
      }
    });
  }
}
