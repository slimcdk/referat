import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatCardModule } from '@angular/material/card';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatListModule } from '@angular/material/list';
import { MeetingService } from '../../services/meeting.service';

@Component({
  selector: 'app-search',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatCardModule,
    MatFormFieldModule,
    MatInputModule,
    MatButtonModule,
    MatIconModule,
    MatListModule
  ],
  templateUrl: './search.component.html',
  styleUrl: './search.component.scss'
})
export class SearchComponent {
  searchQuery: string = '';
  isSearching: boolean = false;
  results: any[] = [];
  searched: boolean = false;

  constructor(private meetingService: MeetingService) {}

  onSearch(): void {
    if (!this.searchQuery.trim()) return;

    this.isSearching = true;
    this.searched = true;

    this.meetingService.semanticSearch(this.searchQuery).subscribe({
      next: (data) => {
        this.results = data;
        this.isSearching = false;
      },
      error: (err) => {
        console.error('Search failed', err);
        this.isSearching = false;
      }
    });
  }

  formatTime(seconds: number): string {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs < 10 ? '0' : ''}${secs}`;
  }
}
