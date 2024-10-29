import os
from qiskit_ibm_runtime import QiskitRuntimeService
from dotenv import load_dotenv


load_dotenv()
 
QiskitRuntimeService.save_account(channel="ibm_quantum", token=os.getenv("IBMX_API_TOKEN"), set_as_default=True)
 
