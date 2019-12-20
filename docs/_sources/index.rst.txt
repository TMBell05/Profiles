.. Profile_Set documentation master file, created by
   sphinx-quickstart on Tue Feb 26 09:13:51 2019.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

oucass-profiles Overview
=======================================

.. toctree::
   :maxdepth: 2
   :caption: Contents:
   :titlesonly:

   Meta
   Profile
   Profile_Set
   Raw_Profile
   Profile_Set
   Thermo_Profile
   Wind_Profile
   plotting
   utils
   Sensor calibration <coefs>



Key Equations
==================

1) Position data to wind

.. math::

   \begin{aligned}
   \mathrm{Speed} &= A \sqrt{\tan{[\arccos{(\cos{(\mathrm{PITCH})} - \cos{(\mathrm{ROLL})})}]}} + B \\
   \\
   \mathrm{Direction} &= \arctan{\Bigg[\frac{-\cos{(\mathrm{YAW})}\sin{(\mathrm{ROLL})}}{\sin{(\mathrm{YAW})}\sin{(\mathrm{ROLL})} + \sin{(\mathrm{PITCH})}\cos{(\mathrm{YAW})}\cos{(\mathrm{ROLL})}} \Bigg]}
   \end{aligned}


2) Thermistor resistance to temperature

.. math::

   \begin{aligned}
   T &= \frac{1}{A + B (log{R}) + C (log{R})^3}
   \end{aligned}


Contact us!
================================

.. raw:: html

   <embed>
   <form name='input' method='POST' action=https://formspree.io/cass@ou.edu>
      Name: <input type="text" name="Name" placeholder="Your name"><br>
      Email: <input type="email" name="_replyto" placeholder="Your email"><br>
      Message: <textarea name="message" placeholder="Type your message here"></textarea><br>
      <input type="submit" value="send">
      <input type="hidden" name="_subject" value="PROFILES INQUIRY">
      <input type="hidden" name="_cc" value="ajacobs@ou.edu"
   </form>
   </embed>
