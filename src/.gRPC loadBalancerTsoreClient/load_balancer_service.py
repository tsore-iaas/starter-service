from concurrent import futures
import grpc
import vm_pb2
import vm_pb2_grpc

class LoadBalancerServicer(vm_pb2_grpc.LoadBalancerServicer):
    def __init__(self):
        self.machine_status = {
            "machine1": "available",
            "machine2": "busy",
        }

    def AllocateVM(self, request, context):
        for machine, status in self.machine_status.items():
            if status == "available":
                self.machine_status[machine] = "busy"
                return vm_pb2.Response(
                    message=f"VM allocated on {machine}", success=True
                )
        return vm_pb2.Response(message="No machines available", success=False)

    def CheckStatus(self, request, context):
        return vm_pb2.ResourceStatus(machine_status=self.machine_status)

def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    vm_pb2_grpc.add_LoadBalancerServicer_to_server(LoadBalancerServicer(), server)
    server.add_insecure_port('[::]:50052')
    print("LoadBalancer Service running on port 50052")
    server.start()
    server.wait_for_termination()

if __name__ == "__main__":
    serve()
