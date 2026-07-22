import { Routes } from '@angular/router';
import { UploadComponent } from './components/upload/upload.component';
import { SearchComponent } from './components/search/search.component';
import { SettingsComponent } from './components/settings/settings.component';

export const routes: Routes = [
  { path: 'upload', component: UploadComponent },
  { path: 'search', component: SearchComponent },
  { path: 'settings', component: SettingsComponent },
  { path: '', redirectTo: 'upload', pathMatch: 'full' },
  { path: '**', redirectTo: 'upload' }
];
