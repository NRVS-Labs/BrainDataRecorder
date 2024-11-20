# BDR: BrainDataRecorder

A simple application for recording and saving recorded data from biosensing devices compatible with [Brainflow](https://brainflow.org/)


## Maintainer Info

- **Owner**: [Leonardo Ferrisi](https://github.com/LeonardoFerrisi)
- **Objective**: *BDR* aims to solve the headache of performing the basic action of data collection with your specific biosensing board. Brainflow is excellent and removing the headache in connecting wireless-capable biosensing devices but has a barrier to entry for those not familiar with writing software to conduct their research / experiments. The solution *BDR* provides is a Graphical User Interface (GUI) that allows the user to select a device, and record data.* 
- **Audience**: Researchers and Developers using EEG and EMG equipment currently compatible with [Brainflow](https://brainflow.readthedocs.io/en/stable/SupportedBoards.html)
- **Maintainers**:
    - [LeonardoFerrisi](https://github.com/LeonardoFerrisi)
    - [alexfigtree](https://github.com/alexfigtree)
- **Technology Stack**:
    - JavaScript
        - React (dev-react)
        - ElectronJS (all branches)
    - Python
        - brainflow (all branches)
        - pandas (all branches)
        - numpy (all branches)
        - flask (all branches)

*Data is saved in the Brain-Data-Format (BDF) or CSV
## Branches

- dev-basic: BDR using ElectronJS with a basic CSS-JS-HTML with a Python Backend architecture. <span style="color: orange;">(INCOMPLETE)</span>
- dev-react: BDR using ElectronJS with a React frontend and a Python Backend. <span style="color: yellow;">(WORKING)</span>
- main: *Informational branch*

