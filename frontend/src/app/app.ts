import { Component, OnInit, signal } from '@angular/core';
import { RouterOutlet, RouterLink, RouterLinkActive } from '@angular/router';
import { CommonModule } from '@angular/common';
import { HttpClient, HttpClientModule } from '@angular/common/http';
import { MatToolbarModule } from '@angular/material/toolbar';
import { MatSidenavModule } from '@angular/material/sidenav';
import { MatListModule } from '@angular/material/list';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [
    CommonModule,
    RouterOutlet,
    RouterLink,
    RouterLinkActive,
    HttpClientModule, // Ensure HttpClientModule is imported for the auto-login
    MatToolbarModule,
    MatSidenavModule,
    MatListModule,
    MatIconModule,
    MatButtonModule
  ],
  templateUrl: './app.html',
  styleUrl: './app.scss'
})
export class App implements OnInit {
  title = signal('Referat');
  isDarkMode = signal(false);

  constructor(private http: HttpClient) {}

  ngOnInit(): void {
    this.ensureAuthenticated();
  }

  ensureAuthenticated(): void {
    const token = localStorage.getItem('access_token');
    
    // For local development and self-hosted use cases without a manual login screen:
    // If no token exists, perform a silent background login with the seeded admin credentials.
    if (!token) {
      this.performSilentLogin();
    } else {
      // Validate the token quickly against a lightweight API check
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

  toggleDarkMode(): void {
    this.isDarkMode.set(!this.isDarkMode());
    if (this.isDarkMode()) {
      document.body.classList.add('dark-theme');
    } else {
      document.body.classList.remove('dark-theme');
    }
  }
}
