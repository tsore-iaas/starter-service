import grpc
from concurrent import futures
import time

import load_balancer_service_pb2
import load_balancer_service_pb2_grpc

class LoadBalancerService(load_balancer_service_pb2_grpc.LoadBalancerServiceServicer):
    def __init__(self):
        # Liste initiale de PCs avec des ressources
        self.pcs = [
            {"pc_id": "PC1", "cpu_usage": 20.0, "ram_usage": 40.0, "status": "active"},
            {"pc_id": "PC2", "cpu_usage": 50.0, "ram_usage": 60.0, "status": "active"},
            {"pc_id": "PC3", "cpu_usage": 10.0, "ram_usage": 25.0, "status": "active"},
        ]

    def UpdatePCResourcesStatus(self, request, context):
        # Met à jour les ressources et le statut d'un PC existant
        for pc in self.pcs:
            if pc["pc_id"] == request.pc_id:
                pc["cpu_usage"] = request.cpu_usage
                pc["ram_usage"] = request.ram_usage
                pc["status"] = request.status
                return load_balancer_service_pb2.StatusResponse(message=f"PC {request.pc_id} updated.", success=True)
        return load_balancer_service_pb2.StatusResponse(message=f"PC {request.pc_id} not found.", success=False)

    def AddPC(self, request, context):
        # Ajoute un nouveau PC à la liste
        new_pc = {
            "pc_id": request.pc_id,
            "cpu_usage": request.cpu_usage,
            "ram_usage": request.ram_usage,
            "status": request.status
        }
        self.pcs.append(new_pc)
        return load_balancer_service_pb2.StatusResponse(message=f"PC {request.pc_id} added.", success=True)

    def RemovePC(self, request, context):
        # Retire un PC de la liste
        for pc in self.pcs:
            if pc["pc_id"] == request.pc_id:
                self.pcs.remove(pc)
                return load_balancer_service_pb2.StatusResponse(message=f"PC {request.pc_id} removed.", success=True)
        return load_balancer_service_pb2.StatusResponse(message=f"PC {request.pc_id} not found.", success=False)

    def AllocateVMToPC(self, request, context):
        # Trouver le PC avec la moindre utilisation des ressources
        best_pc = min(self.pcs, key=lambda pc: pc["cpu_usage"] + pc["ram_usage"] if pc["status"] == "active" else float('inf'))
        if best_pc:
            best_pc_id = best_pc["pc_id"]
            message = f"VM {request.vm_id} allocated to {best_pc_id} using template {request.template_id}."
            return load_balancer_service_pb2.VMAllocationResponse(pc_id=best_pc_id, message=message)
        else:
            return load_balancer_service_pb2.VMAllocationResponse(pc_id="", message="No available PC for allocation.")


def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    load_balancer_service_pb2_grpc.add_LoadBalancerServiceServicer_to_server(LoadBalancerService(), server)
    server.add_insecure_port('[::]:50052')
    print("LoadBalancerService running on port 50052...")
    server.start()
    server.wait_for_termination()


if __name__ == '__main__':
    serve()
