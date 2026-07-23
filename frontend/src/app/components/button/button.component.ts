import { Component, input, ViewEncapsulation } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';

@Component({
  selector: 'app-button',
  standalone: true,
  imports: [CommonModule, MatButtonModule, MatIconModule],
  template: `
    <button mat-button 
            [type]="type()"
            [class]="getButtonClasses()"
            [disabled]="disabled()">
      <mat-icon *ngIf="icon()">{{ icon() }}</mat-icon>
      <span class="btn-text" *ngIf="text()">{{ text() }}</span>
    </button>
  `,
  styles: [`
    :host {
      display: inline-flex;
      vertical-align: middle;
    }
  `],
  encapsulation: ViewEncapsulation.None // Let the global .action-btn classes target the button wrapper cleanly
})
export class AppButton {
  // Leverage modern Angular 17.1+ Signal inputs for type safety and Zoneless reactive tracking
  icon = input<string>('');
  text = input<string>('');
  color = input<'primary' | 'accent' | 'warn' | ''>('');
  disabled = input<boolean>(false);
  type = input<string>('button');

  getButtonClasses(): string {
    const classes = ['action-btn'];
    const col = this.color();
    if (col === 'primary') classes.push('btn-primary');
    else if (col === 'accent') classes.push('btn-accent');
    else if (col === 'warn') classes.push('btn-warn');
    return classes.join(' ');
  }
}
