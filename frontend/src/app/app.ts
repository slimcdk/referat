import { Component, OnInit, OnDestroy, signal, inject } from '@angular/core';
import { RouterOutlet, RouterLink, RouterLinkActive, Router } from '@angular/router';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { HttpClient, HttpClientModule } from '@angular/common/http';
import { Subject, Subscription } from 'rxjs';
import { debounceTime, distinctUntilChanged } from 'rxjs/operators';
import { MatToolbarModule } from '@angular/material/toolbar';
import { MatSidenavModule } from '@angular/material/sidenav';
import { MatListModule } from '@angular/material/list';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatMenuModule } from '@angular/material/menu';
import { MeetingService } from './services/meeting.service';
import { AppButton } from './components/button/button.component';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [
    CommonModule,
    RouterOutlet,
    RouterLink,
    RouterLinkActive,
    FormsModule,
    HttpClientModule,
    MatToolbarModule,
    MatSidenavModule,
    MatListModule,
    MatIconModule,
    MatButtonModule,
    MatTooltipModule,
    MatMenuModule,
    AppButton
  ],
  templateUrl: './app.html',
  styleUrl: './app.scss'
})
export class App implements OnInit, OnDestroy {
  private http = inject(HttpClient);
  private router = inject(Router);
  private meetingService = inject(MeetingService);

  title = signal('Referat');
  
  // 3-State Dynamic Theme Management (system | light | dark)
  themeMode = signal<'light' | 'dark' | 'system'>('system');
  isDarkMode = signal<boolean>(false); // Read-only helper state for CSS body bindings

  versionInfo = signal<any>(null); // Dynamic Git version/commit details
  
  // Advanced Global Search State
  navbarSearchQuery: string = '';
  isSearchActive: boolean = false;
  isSearching: boolean = false;
  searchResults: any[] = [];
  
  private searchSubject = new Subject<string>();
  private searchSubscription: Subscription | null = null;

  ngOnInit(): void {
    this.ensureAuthenticated();
    this.setupDebouncedSearch();
    this.loadVersionInfo();
    this.setupSystemThemeDetection();
  }

  setupSystemThemeDetection(): void {
    const darkMedia = window.matchMedia('(prefers-color-scheme: dark)');
    
    // Read cached preference or default to system
    const savedPreference = localStorage.getItem('theme_preference') as 'light' | 'dark' | 'system' | null;
    if (savedPreference) {
      this.themeMode.set(savedPreference);
    } else {
      this.themeMode.set('system');
    }

    this.applyTheme();

    // Listen to real-time system OS theme preference swaps (e.g. day/night automations)
    darkMedia.addEventListener('change', (e) => {
      if (this.themeMode() === 'system') {
        this.applyTheme();
      }
    });
  }

  cycleThemeMode(): void {
    const current = this.themeMode();
    let next: 'light' | 'dark' | 'system' = 'system';
    
    // Cycle state machine: system -> light -> dark -> system
    if (current === 'system') {
      next = 'light';
    } else if (current === 'light') {
      next = 'dark';
    } else {
      next = 'system';
    }

    this.themeMode.set(next);
    localStorage.setItem('theme_preference', next);
    this.applyTheme();
  }

  private applyTheme(): void {
    const mode = this.themeMode();
    const systemDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    
    let isDark = false;
    if (mode === 'dark') {
      isDark = true;
    } else if (mode === 'light') {
      isDark = false;
    } else {
      // System mode: defer to OS prefers-color-scheme
      isDark = systemDark;
    }

    this.isDarkMode.set(isDark);

    if (isDark) {
      document.body.classList.add('dark-theme');
      document.documentElement.style.setProperty('color-scheme', 'dark');
    } else {
      document.body.classList.remove('dark-theme');
      document.documentElement.style.setProperty('color-scheme', 'light');
    }
  }

  getThemeTooltip(): string {
    const mode = this.themeMode();
    if (mode === 'system') {
      return 'Tema: System (følger computeren)';
    } else if (mode === 'light') {
      return 'Tema: Lys';
    } else {
      return 'Tema: Mørk';
    }
  }

  getThemeIcon(): string {
    const mode = this.themeMode();
    if (mode === 'system') {
      return 'settings_brightness'; // Multi-brightness/system brightness icon
    } else if (mode === 'light') {
      return 'light_mode'; // Sun icon
    } else {
      return 'dark_mode'; // Moon icon
    }
  }

  // --- Advanced Autocomplete Search Logic ---
  setupDebouncedSearch(): void {
    this.searchSubscription = this.searchSubject.pipe(
      debounceTime(500), // Wait exactly 500ms after user stops typing
      distinctUntilChanged()
    ).subscribe(query => {
      this.executeSearch(query);
    });
  }

  openSearch(): void {
    this.isSearchActive = true;
    if (this.navbarSearchQuery.trim()) {
      this.isSearching = true;
      this.searchSubject.next(this.navbarSearchQuery);
    }
  }

  closeSearch(): void {
    this.isSearchActive = false;
    this.isSearching = false;
    this.navbarSearchQuery = '';
    this.searchResults = [];
  }

  onSearchChange(query: string): void {
    if (!query.trim()) {
      this.searchResults = [];
      this.isSearching = false;
      return;
    }
    this.isSearching = true;
    this.searchSubject.next(query);
  }

  executeSearch(query: string): void {
    if (!query.trim()) {
      this.searchResults = [];
      this.isSearching = false;
      return;
    }

    this.meetingService.semanticSearch(query).subscribe({
      next: (data) => {
        this.searchResults = data;
        this.isSearching = false;
      },
      error: (err) => {
        console.error('Global search failed', err);
        this.isSearching = false;
      }
    });
  }

  triggerNavbarSearch(): void {
    if (!this.navbarSearchQuery.trim()) return;
    this.executeSearch(this.navbarSearchQuery);
  }

  goToResult(result: any): void {
    this.closeSearch();
    
    if (result.meeting_id) {
      this.router.navigate(['/referater'], { queryParams: { meeting_id: result.meeting_id } });
    } else {
      this.router.navigate(['/clips']);
    }
  }

  formatTime(seconds: number): string {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs < 10 ? '0' : ''}${secs}`;
  }

  triggerGlobalUpload(): void {
    this.closeSearch();
    this.router.navigate(['/clips'], { queryParams: { action: 'upload', t: Date.now() } });
  }

  triggerGlobalRecord(): void {
    this.closeSearch();
    this.router.navigate(['/clips'], { queryParams: { action: 'record', t: Date.now() } });
  }

  loadVersionInfo(): void {
    this.http.get<any>('/version.json').subscribe({
      next: (data) => {
        this.versionInfo.set(data);
      },
      error: (err) => {
        console.warn('Could not read version.json asset, using fallbacks.', err);
      }
    });
  }

  ngOnDestroy(): void {
    if (this.searchSubscription) {
      this.searchSubscription.unsubscribe();
    }
  }

  ensureAuthenticated(): void {
    const token = localStorage.getItem('access_token');
    
    if (!token) {
      this.performSilentLogin();
    } else {
      this.http.get('http://localhost:5000/api/health', {
        headers: { 'Authorization': `Bearer ${token}` }
      }).subscribe({
        error: (err) => {
          if (err.status === 401) {
            console.warn('Eksisterende token er udløbet eller ugyldig. Gen-fornyer token...');
            localStorage.removeItem('access_token');
            this.performSilentLogin();
          }
        }
      });
    }
  }

  private performSilentLogin(): void {
    console.log('Udfører tavs auto-login med dev-administrator...');
    this.http.post<any>('http://localhost:5000/api/auth/login', {
      email: 'admin@referat.io',
      password: 'admin_secure_pass_change_me'
    }).subscribe({
      next: (res) => {
        if (res && res.access_token) {
          localStorage.setItem('access_token', res.access_token);
          console.log('Tavs auto-login lykkedes! Genindlæser applikationen...');
          window.location.reload();
        }
      },
      error: (err) => {
        console.error('Tavs auto-login fejlede. Kontroller om FastAPI-backend er kørende.', err);
      }
    });
  }
}
