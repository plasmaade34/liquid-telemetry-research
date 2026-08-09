import os
import shutil
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns

def run_simulation():
    # Set style
    sns.set_theme(style='whitegrid', palette='colorblind', font='DejaVu Sans')
    
    # Constants
    R = 0.1  # Radius of vessel (10 cm = 0.1 m)
    SF = 1.5  # Safety Factor
    ATM_TO_PA = 101325  # 1 Atmosphere in Pascals
    
    # Pressures to simulate (0 to 10 Atmospheres)
    pressures_atm = np.linspace(0.1, 10.0, 100)
    pressures_pa = pressures_atm * ATM_TO_PA
    
    # Material properties
    # Sources: 304 Stainless Steel [1, 18], Aluminum 6061-T6 [18], Titanium Grade 5 (standard aerospace grade)
    materials = {
        '304 Stainless Steel': {
            'density': 8000.0,      # kg/m^3 (8.0 g/cm^3) [18]
            'yield_strength': 2.15e8, # Pa (215 MPa)
            'youngs_modulus': 1.93e11, # Pa (193 GPa)
            'poisson_ratio': 0.29
        },
        '6061-T6 Aluminum': {
            'density': 2700.0,      # kg/m^3 (2.7 g/cm^3) [18]
            'yield_strength': 2.76e8, # Pa (276 MPa)
            'youngs_modulus': 6.89e10, # Pa (68.9 GPa)
            'poisson_ratio': 0.33
        },
        'Titanium Grade 5': {
            'density': 4430.0,      # kg/m^3 (4.43 g/cm^3)
            'yield_strength': 8.80e8, # Pa (880 MPa)
            'youngs_modulus': 1.14e11, # Pa (114 GPa)
            'poisson_ratio': 0.34
        }
    }
    
    # Create lists to gather data for plotting
    data_list = []
    
    for mat_name, props in materials.items():
        rho = props['density']
        sigma_y = props['yield_strength']
        E = props['youngs_modulus']
        nu = props['poisson_ratio']
        
        for p_atm, p_pa in zip(pressures_atm, pressures_pa):
            # 1. Hoop Stress Wall Thickness Requirement (Barlow's Formula)
            t_hoop = (p_pa * R * SF) / sigma_y
            
            # 2. Elastic Shell Buckling Wall Thickness Requirement (Timoshenko's Stability)
            t_buckle = R * ((4.0 * p_pa * SF * (1 - nu**2)) / E) ** (1.0/3.0)
            
            # Actual thickness must withstand both mechanisms
            t_req = max(t_hoop, t_buckle)
            
            # Mass per unit length: Area of the cross section of the tube * density
            # Area = pi * ((R + t)^2 - R^2)
            mass_per_m = np.pi * ((R + t_req)**2 - R**2) * rho
            
            data_list.append({
                'Material': mat_name,
                'Pressure_Atm': p_atm,
                't_hoop_mm': t_hoop * 1000,
                't_buckle_mm': t_buckle * 1000,
                't_req_mm': t_req * 1000,
                'Mass_kg_m': mass_per_m
            })
            
    df = pd.DataFrame(data_list)
    
    # Create Side-by-Side Comparison plots
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
    
    # Title-as-takeaway (MANDATORY per data-craft)
    fig.suptitle('Titanium Grade 5 Reduces Vessel Mass by 35% vs. Stainless Steel While Remaining 15% Thinner Than Aluminum', 
                 fontsize=14, fontweight='bold', y=0.98)
    
    # Palette choice: colorblind
    colors = sns.color_palette('colorblind', n_colors=3)
    palette_dict = {
        '304 Stainless Steel': colors[0],
        '6061-T6 Aluminum': colors[1],
        'Titanium Grade 5': colors[2]
    }
    
    # Left Plot: Required Wall Thickness (t_req)
    sns.lineplot(data=df, x='Pressure_Atm', y='t_req_mm', hue='Material', ax=ax1, palette=palette_dict, linewidth=2.5)
    ax1.set_title('Required Wall Thickness to Prevent Tearing & Buckling', fontsize=12, fontweight='bold', pad=10)
    ax1.set_xlabel('External Differential Pressure (Atmospheres)')
    ax1.set_ylabel('Required Wall Thickness (mm)')
    
    # Right Plot: Vessel Mass per Unit Length
    sns.lineplot(data=df, x='Pressure_Atm', y='Mass_kg_m', hue='Material', ax=ax2, palette=palette_dict, linewidth=2.5)
    ax2.set_title('Vessel Mass per Unit Length vs. Pressure', fontsize=12, fontweight='bold', pad=10)
    ax2.set_xlabel('External Differential Pressure (Atmospheres)')
    ax2.set_ylabel('Linear Mass of Vessel (kg/m)')
    
    # Add annotations directly onto the right plot to show specific values at 10 Atm
    for name, color in palette_dict.items():
        val_10 = df[(df['Material'] == name) & (df['Pressure_Atm'] > 9.8)].iloc[-1]
        ax2.annotate(f"{val_10['Mass_kg_m']:.2f} kg/m", 
                     xy=(10.0, val_10['Mass_kg_m']), 
                     xytext=(10.1, val_10['Mass_kg_m']),
                     fontsize=9, fontweight='bold', color=color,
                     arrowprops=dict(arrowstyle="->", color=color, lw=1))
        
        # Also mark thickness on left plot
        val_10_t = df[(df['Material'] == name) & (df['Pressure_Atm'] > 9.8)].iloc[-1]
        ax1.annotate(f"{val_10_t['t_req_mm']:.2f} mm", 
                     xy=(10.0, val_10_t['t_req_mm']), 
                     xytext=(10.1, val_10_t['t_req_mm']),
                     fontsize=9, fontweight='bold', color=color,
                     arrowprops=dict(arrowstyle="->", color=color, lw=1))
        
    ax1.legend(loc='upper left')
    ax2.legend(loc='upper left')
    
    # Despine and finish
    sns.despine()
    plt.tight_layout(pad=2.0)
    
    os.makedirs('/workspace/scratch', exist_ok=True)
    fig_path = '/workspace/scratch/substrate_optimization.png'
    fig.savefig(fig_path, dpi=150, bbox_inches='tight')
    plt.close()
    
    print(f"Simulation run successfully. Plot saved to {fig_path}")

if __name__ == '__main__':
    run_simulation()
