#!/usr/bin/env python3
"""
Script de migración para video-to-ascii
Ayuda a los usuarios a migrar del sistema antiguo al nuevo
"""

import sys
import subprocess
import os

def main():
    print("🎬 Video-to-ASCII Migration Helper")
    print("="*50)
    
    # Detectar si están tratando de usar el método antiguo
    old_command = any('--install-option' in arg and '--with-audio' in arg for arg in sys.argv)
    
    if old_command or '--help' in sys.argv or len(sys.argv) == 1:
        print("\n📢 NOTICE: Installation method has changed!")
        print("\n❌ Old way (no longer works):")
        print("   pip3 install video-to-ascii --install-option=\"--with-audio\"")
        
        print("\n✅ New ways:")
        print("   pip install video-to-ascii          # Basic installation")
        print("   pip install video-to-ascii[audio]   # With audio support")  
        print("   pip install video-to-ascii[all]     # Everything included")
        
        if not ('--help' in sys.argv or len(sys.argv) == 1):
            print("\n🔄 Auto-installing with audio support...")
            try:
                subprocess.run([sys.executable, '-m', 'pip', 'install', 'video-to-ascii[audio]'], check=True)
                print("✅ Installation completed successfully!")
            except subprocess.CalledProcessError:
                print("❌ Installation failed. Please try manually:")
                print("   pip install video-to-ascii[audio]")
                sys.exit(1)
    else:
        print("Usage: python migrate.py")

if __name__ == '__main__':
    main()