import { Routes } from '@angular/router';
import { UploadComponent } from './components/upload/upload.component';
import { ClipsComponent } from './components/clips/clips.component';
import { SearchComponent } from './components/search/search.component';
import { SettingsComponent } from './components/settings/settings.component';

export const routes: Routes = [
  { path: 'referater', component: UploadComponent },
  { path: 'clips', component: ClipsComponent },
  { path: 'search', component: SearchComponent },
  { path: 'settings', component: SettingsComponent },
  { path: '', redirectTo: 'referater', pathMatch: 'full' },
  { path: '**', redirectTo: 'referater' }
];
