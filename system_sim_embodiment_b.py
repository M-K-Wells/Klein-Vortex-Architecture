"""
TITLE: Simulation Core for Project Talaria: Validation of Embodiment B
       (Leidenfrost-Stabilized MHD Synthesis)
DATE:  December 12, 2025
LICENSE: GNU General Public License v3.0 (GPLv3)

DESCRIPTION:
Computational proof-of-concept for the "Klein-Vortex Architecture".
Validates continuous MWCNT growth > 1.0 meter via inductive heating
in liquid hydrocarbons (Dodecane) under high-precision magnetic slip control.

IDENTITY PROOF (SHA-256 Hash): 357fe2771c06ac5518dce8761b4fb32c6a487617e318e0ea2d5c83e44420ee7c
"""

import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import pandas as pd

# --- CONSTANTS v8.0 (Validation Run: 1 Meter Limit) ---

# Physics & Fluid Dynamics
G = 9.81
RHO_FLUID = 750.0       # Dodecane (approx.)
RHO_PARTICLE = 8900.0   # Co-Fe / Co-Mo Alloy

# OPTIMIZATION 1: High-Temperature Regime (180°C)
# Viscosity drops from 1.2e-3 to 0.4e-3 Pa.s, significantly reducing drag.
VISCOSITY = 0.4e-3      

# Reactor Geometry
R_TANK = 0.05           # Radius (m)
LIFT_SPEED = 0.0004     # 0.4 mm/s

# Process Control (High Precision Mode)
RPM_FLUID = 100.0
# OPTIMIZATION 2: Precision Slip Control
# Magnet set to 99.95 RPM -> Only 0.05 RPM slip.
# This minimizes transverse shear forces to allow macroscopic growth.
RPM_MAGNET = 99.95       
MAGNET_STIFFNESS = 2e-5 

# Catalyst & Nanotube Properties
R_CORE = 3.0e-6         # 3 µm Janus Particle
R_CNT = 20e-9           # 20 nm MWCNT
GROWTH_RATE = 80e-6     # 80 µm/s (Super-Growth Kinetic)

# OPTIMIZATION 3: Enhanced Anchoring
# Co-Mo catalyst provides chemical anchoring > 400 nN before lift-off.
ADHESION_LIMIT = 400e-9 

# Simulation Constraints
DT = 0.0005             # Time step (s)
TOTAL_TIME = 12500.0    # 12,500 s (~3.5 hours) for > 1.0 meter target

class ReactorSystem:
    def __init__(self):
        self.pos = np.array([R_TANK, 0.0, 0.0])
        self.cnt_length = 1e-9 
        self.break_counter = 0
        self.max_length_record = 0.0
        
        # Thermodynamics State
        self.thermal_energy = 0.0 
        self.r_vapor = 0.0
        self.power_input = 0.0
        
        # PID Controller State
        self.pid_err_sum = 0.0
        self.pid_last_err = 0.0
        self.current_z_vel_real = 0.0
        
    def get_fluid_velocity_field(self, pos):
        # Taylor-Couette flow approximation
        omega_fluid = (RPM_FLUID / 60.0) * 2 * np.pi
        r = np.sqrt(pos[0]**2 + pos[1]**2)
        if r < 1e-6: return np.array([0,0, LIFT_SPEED])
        
        v_tan_mag = omega_fluid * r
        tan_vec = np.array([-pos[1], pos[0], 0]) / r
        
        v_fluid = (tan_vec * v_tan_mag)
        v_fluid[2] = LIFT_SPEED 
        return v_fluid

    def get_magnetic_target(self, t):
        # Magnetic trap position (rotating slightly slower)
        omega_mag = (RPM_MAGNET / 60.0) * 2 * np.pi
        angle = omega_mag * t
        return np.array([R_TANK * np.cos(angle), R_TANK * np.sin(angle), self.pos[2]])

    def step(self, t):
        # 1. Soft-Start Logic
        # Ramps up target velocity over 20s to prevent PID overshoot
        ramp_time = 20.0 
        if t < ramp_time:
            current_target_vel = LIFT_SPEED * (t / ramp_time)
        else:
            current_target_vel = LIFT_SPEED
            
        # 2. Chemical Growth
        self.cnt_length += GROWTH_RATE * DT
        if self.cnt_length > self.max_length_record:
            self.max_length_record = self.cnt_length
        
        # 3. PID Control Loop (Induction Power)
        noise = np.random.normal(0, 0.0002) # Sensor noise simulation
        measured_vel = self.current_z_vel_real + noise
        
        z_error = current_target_vel - measured_vel
        
        self.pid_err_sum += z_error * DT
        self.pid_err_sum = np.clip(self.pid_err_sum, -0.5, 0.5) # Anti-windup
        d_err = (z_error - self.pid_last_err) / DT
        
        # Tuned PID parameters for thermal inertia
        kp, ki, kd = 80000.0, 5000.0, 500.0
        adj = (kp * z_error) + (ki * self.pid_err_sum) + (kd * d_err)
        
        self.power_input += adj * DT
        self.power_input = np.clip(self.power_input, 0, 150) # Max Power (Arbitrary Units)
        self.pid_last_err = z_error
        
        # 4. Thermodynamics (Leidenfrost Mechanism)
        # Energy balance: dE = (PowerIn - CoolingLoss) * dt
        cooling_loss = self.thermal_energy * 2.0 
        d_energy = (self.power_input - cooling_loss) * DT
        self.thermal_energy += d_energy
        self.thermal_energy = max(0, self.thermal_energy)
        
        # Vapor shell radius derived from thermal energy
        k_vol = 1.0e-13 
        self.r_vapor = (self.thermal_energy * k_vol)**(1/3)

        # 5. Forces & Mass
        vol_core = (4/3) * np.pi * R_CORE**3
        vol_vapor = (4/3) * np.pi * self.r_vapor**3
        vol_total = vol_core + vol_vapor 
        
        mass_particle = vol_core * RHO_PARTICLE
        vol_cnt = np.pi * (R_CNT**2) * self.cnt_length
        mass_cnt = vol_cnt * 2200.0 # Density of Graphite/CNT
        total_mass = mass_particle + mass_cnt
        
        # Buoyancy vs Gravity
        f_buoy = vol_total * RHO_FLUID * G
        f_grav = total_mass * G
        f_z_net = f_buoy - f_grav
        
        # Magnetic & Centrifugal Forces
        target_pos = self.get_magnetic_target(t)
        dist_vec = target_pos - self.pos
        dist_vec[2] = 0 
        f_mag = dist_vec * MAGNET_STIFFNESS
        
        omega_fluid = (RPM_FLUID / 60.0) * 2 * np.pi
        f_cent = total_mass * (omega_fluid**2) * np.array([self.pos[0], self.pos[1], 0])
        
        # 6. Hydrodynamics (Slender Body Theory)
        r_eff_sphere = R_CORE + self.r_vapor
        gamma_sphere = 6 * np.pi * VISCOSITY * r_eff_sphere
        
        if self.cnt_length > 10 * R_CNT:
            # Aspect Ratio correction for long filaments
            eps = (2 * self.cnt_length) / R_CNT
            denom = np.log(eps) - 0.5
            gamma_cnt = (2 * np.pi * VISCOSITY * self.cnt_length) / denom
        else:
            gamma_cnt = 0
            
        gamma_total = gamma_sphere + gamma_cnt
        
        # Motion Integration
        f_external = f_mag + f_cent
        f_external[2] += f_z_net
        
        v_drift = f_external / gamma_total
        v_drift_mag = np.linalg.norm(v_drift)
        v_fluid = self.get_fluid_velocity_field(self.pos)
        v_total = v_fluid + v_drift
        
        self.pos += v_total * DT
        self.current_z_vel_real = v_total[2]
        
        # 7. Tear-Off Analysis (Mechanical Failure Check)
        # Tension is generated by the drag on the filament due to slip
        f_tension = v_drift_mag * gamma_cnt
        broken = False
        
        # Check against adhesion limit (ignoring first 5s stabilization)
        if f_tension > ADHESION_LIMIT and t > 5.0:
            broken = True
            self.break_counter += 1
            self.cnt_length = 1e-9 # Reset length (Snap)
        
        return self.pos, self.cnt_length, self.power_input, current_target_vel, self.r_vapor, f_tension, broken

# --- MAIN EXECUTION ---
if __name__ == "__main__":
    # A. CONFIGURATION DASHBOARD
    print("="*100)
    print("      PROJECT TALARIA: EMBODIMENT B VALIDATION (1 METER RUN)")
    print("="*100)
    print(f" PHYSICS PARAMETERS")
    print(f"  - Fluid Viscosity  : {VISCOSITY} Pa.s (Dodecane @ 180C)")
    print(f"  - Adhesion Limit   : {ADHESION_LIMIT*1e9:.1f} nN (Co-Mo Interface)")
    print("-" * 100)
    print(f" PROCESS CONTROL")
    print(f"  - Lift Speed       : {LIFT_SPEED*1000:.2f} mm/s")
    print(f"  - Fluid Rotation   : {RPM_FLUID} RPM")
    print(f"  - Magnet Rotation  : {RPM_MAGNET} RPM")
    print("-" * 100)
    print(f" TARGETS")
    print(f"  - Growth Rate      : {GROWTH_RATE*1e6:.1f} µm/s")
    print(f"  - Simulation Time  : {TOTAL_TIME} s")
    print("="*100)
    print("\nInitializing System...\n")

    sim = ReactorSystem()
    history_pos = []
    history_meta = [] 

    # B. DATA LOGGING
    # Header
    print(f"{'Time':>6} | {'Progress':>10} | {'Height Z':>9} | {'CNT Len':>9} | {'Vel (Act)':>10} | {'Power':>6} | {'Bubble r':>8} | {'Tension':>8} | {'Status':>6}")
    print(f"{'[s]':>6} | {'[%]':>10} | {'[mm]':>9} | {'[mm]':>9} | {'[mm/s]':>10} | {'Unit':>6} | {'[µm]':>8} | {'[nN]':>8} | {' ':>6}")
    print("-" * 100)

    steps = int(TOTAL_TIME/DT)
    log_interval = steps // 25 # Log every 4%

    for i in range(steps):
        t = i * DT
        pos, length, pwr, tgt, r_vap, tension, is_broken = sim.step(t)
        
        # Data Sampling (Reduced rate for plotting)
        if i % 1000 == 0: 
            history_pos.append(pos.copy())
            # Meta: Time, Len, Pwr, Tgt, Vel, Radius, Tension
            history_meta.append([t, length, pwr, tgt, sim.current_z_vel_real, r_vap, tension])
            
        # Console Output
        status = "OK"
        if is_broken:
            status = "!!!SNAP"
            print(f"{t:6.1f} | {i/steps*100:9.1f}% | {pos[2]*1000:9.2f} | {length*1000:9.2f} | {sim.current_z_vel_real*1000:9.3f} | {pwr:6.1f} | {r_vap*1e6:8.1f} | {tension*1e9:8.1f} | {status}")
        
        elif i % log_interval == 0 or i == steps - 1:
            progress = (i / steps) * 100
            print(f"{t:6.1f} | {progress:9.1f}% | {pos[2]*1000:9.2f} | {length*1000:9.2f} | {sim.current_z_vel_real*1000:9.3f} | {pwr:6.1f} | {r_vap*1e6:8.1f} | {tension*1e9:8.1f} | {status}")

    print("-" * 100)
    print(f"Simulation Complete.")
    print(f"Total Snaps:      {sim.break_counter}")
    print(f"Max Length Achieved: {sim.max_length_record*1000:.2f} mm")

    # C. VISUALIZATION
    pos_arr = np.array(history_pos)
    meta_arr = np.array(history_meta)

    # Attempt to set style, fallback to default if unavailable
    try: plt.style.use('seaborn-v0_8-darkgrid')
    except: pass

    fig = plt.figure(figsize=(14, 10))

    # 1. 3D Trajectory
    ax1 = fig.add_subplot(2, 2, 1, projection='3d')
    sc = ax1.scatter(pos_arr[:,0], pos_arr[:,1], pos_arr[:,2], 
                     c=meta_arr[:,2], cmap='plasma', s=1, alpha=0.5)
    ax1.set_title("3D Path (Color = Inductive Power)")
    ax1.set_xlabel('X (m)')
    ax1.set_ylabel('Y (m)')
    ax1.set_zlabel('Height Z (m)')
    fig.colorbar(sc, ax=ax1, label='Power Input', shrink=0.6)

    # 2. Bubble Radius (Thermodynamics)
    ax2 = fig.add_subplot(2, 2, 2)
    ax2.plot(meta_arr[:,0], meta_arr[:,5] * 1e6, color='darkorange', lw=1.5)
    ax2.set_title('Leidenfrost Shell Evolution')
    ax2.set_ylabel('Vapor Radius (µm)')
    ax2.set_xlabel('Time (s)')
    ax2.grid(True)
    ax2.axhline(R_CORE*1e6, color='black', linestyle='--', alpha=0.3, label='Particle Core')
    ax2.legend()

    # 3. Growth & Stress Analysis
    ax3 = fig.add_subplot(2, 2, 3)
    c_len = 'tab:purple'
    ax3.set_xlabel('Time (s)')
    ax3.set_ylabel('CNT Length (mm)', color=c_len)
    ax3.plot(meta_arr[:,0], meta_arr[:,1] * 1000, color=c_len, linewidth=2, label='Length')
    ax3.tick_params(axis='y', labelcolor=c_len)
    
    # Tension on secondary axis
    ax3r = ax3.twinx()
    c_ten = 'tab:red'
    ax3r.set_ylabel('Tensile Stress (nN)', color=c_ten)
    ax3r.plot(meta_arr[:,0], meta_arr[:,6] * 1e9, color=c_ten, alpha=0.4, lw=1, label='Drag Force')
    ax3r.axhline(ADHESION_LIMIT*1e9, color='red', linestyle='--', alpha=0.5, label='Adhesion Limit')
    ax3r.tick_params(axis='y', labelcolor=c_ten)
    ax3.set_title('Growth vs. Mechanical Limit')

    # 4. Process Stability
    ax4 = fig.add_subplot(2, 2, 4)
    smooth_vel = pd.Series(meta_arr[:,4]*1000).rolling(50).mean()
    ax4.plot(meta_arr[:,0], meta_arr[:,4] * 1000, color='blue', alpha=0.2, lw=0.5)
    ax4.plot(meta_arr[:,0], smooth_vel, color='navy', lw=1.5, label='Actual (Trend)')
    ax4.plot(meta_arr[:,0], meta_arr[:,3] * 1000, color='green', linestyle='--', label='Target')
    ax4.set_title('Lift Velocity Control')
    ax4.set_ylabel('Velocity (mm/s)')
    ax4.set_xlabel('Time (s)')
    ax4.legend(loc='lower right')

    plt.tight_layout()
    plt.savefig('embodiment_b_validation_1m.png')
    print("Export Complete. Saved as 'embodiment_b_validation_1m.png'.")
