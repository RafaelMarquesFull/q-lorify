import { useState, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Badge } from "@/components/ui/badge"
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuLabel, DropdownMenuSeparator, DropdownMenuTrigger } from "@/components/ui/dropdown-menu"
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { MoreHorizontal, User, ShieldAlert, Wallet } from "lucide-react"
import api from "@/lib/api"
import { toast } from "sonner"

interface User {
    id: string
    name: string
    email: string
    role: string
    balance: number
    createdAt: string
}

export default function UsersPage() {
    const [users, setUsers] = useState<User[]>([])
    const [selectedUser, setSelectedUser] = useState<User | null>(null)
    const [isBalanceOpen, setIsBalanceOpen] = useState(false)
    const [amount, setAmount] = useState("")
    const [type, setType] = useState("CREDIT") // CREDIT or DEBIT
    const [description, setDescription] = useState("")

    useEffect(() => {
        fetchUsers()
    }, [])

    async function fetchUsers() {
        try {
            const res = await api.get("/admin/users")
            setUsers(res.data)
        } catch (error) {
            toast.error("Failed to fetch users")
        }
    }

    async function updateRole(userId: string, role: string) {
        try {
            await api.patch("/admin/users", { userId, role })
            toast.success(`User role updated to ${role}`)
            fetchUsers()
        } catch (error) {
            toast.error("Failed to update user role")
        }
    }

    async function handleBalanceUpdate() {
        if (!selectedUser || !amount) return

        try {
            await api.post("/admin/users/balance", {
                userId: selectedUser.id,
                amount: parseFloat(amount),
                type,
                description: description || "Ajuste manual (Admin)"
            })
            toast.success("Balance updated successfully")
            setIsBalanceOpen(false)
            setAmount("")
            setDescription("")
            fetchUsers()
        } catch (error) {
            console.error(error)
            toast.error("Failed to update balance")
        }
    }

    return (
        <div className="p-8 space-y-8 text-white">
            <div className="flex items-center justify-between">
                <h2 className="text-3xl font-bold tracking-tight">Users</h2>
                <Badge variant="outline" className="text-white border-white/20">
                    Total Users: {users.length}
                </Badge>
            </div>

            <div className="rounded-md border border-white/10">
                <Table>
                    <TableHeader className="bg-white/5">
                        <TableRow className="border-white/10 hover:bg-transparent">
                            <TableHead className="text-white">User</TableHead>
                            <TableHead className="text-white">Email</TableHead>
                            <TableHead className="text-white">Role</TableHead>
                            <TableHead className="text-white">Balance</TableHead>
                            <TableHead className="text-white">Joined</TableHead>
                            <TableHead className="text-right text-white">Actions</TableHead>
                        </TableRow>
                    </TableHeader>
                    <TableBody>
                        {users.map((user) => (
                            <TableRow key={user.id} className="border-white/10 hover:bg-white/5">
                                <TableCell className="font-medium flex items-center gap-2">
                                    <div className="h-8 w-8 rounded-full bg-white/10 flex items-center justify-center">
                                        <User className="h-4 w-4 text-white" />
                                    </div>
                                    {user.name || "No Name"}
                                </TableCell>
                                <TableCell className="text-white/60">{user.email}</TableCell>
                                <TableCell>
                                    <Badge className={user.role === 'ADMIN' ? 'bg-red-500/20 text-red-500 hover:bg-red-500/30' : 'bg-white/10 text-white hover:bg-white/20'}>
                                        {user.role}
                                    </Badge>
                                </TableCell>
                                <TableCell className="text-white/80 font-mono">
                                    {new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(user.balance || 0)}
                                </TableCell>
                                <TableCell className="text-white/60">
                                    {new Date(user.createdAt).toLocaleDateString()}
                                </TableCell>
                                <TableCell className="text-right">
                                    <DropdownMenu>
                                        <DropdownMenuTrigger asChild>
                                            <Button variant="ghost" className="h-8 w-8 p-0">
                                                <span className="sr-only">Open menu</span>
                                                <MoreHorizontal className="h-4 w-4 text-white" />
                                            </Button>
                                        </DropdownMenuTrigger>
                                        <DropdownMenuContent align="end" className="bg-zinc-950 border-white/10 text-white">
                                            <DropdownMenuLabel>Actions</DropdownMenuLabel>
                                            <DropdownMenuSeparator className="bg-white/10" />
                                            <DropdownMenuItem onClick={() => { setSelectedUser(user); setIsBalanceOpen(true) }} className="hover:bg-white/5 cursor-pointer">
                                                <Wallet className="mr-2 h-4 w-4" /> Manage Balance
                                            </DropdownMenuItem>
                                            {user.role !== 'ADMIN' && (
                                                <DropdownMenuItem onClick={() => updateRole(user.id, 'ADMIN')} className="text-red-500 hover:bg-red-500/10 cursor-pointer">
                                                    <ShieldAlert className="mr-2 h-4 w-4" /> Promote to Admin
                                                </DropdownMenuItem>
                                            )}
                                            {user.role === 'ADMIN' && (
                                                <DropdownMenuItem onClick={() => updateRole(user.id, 'CLIENT')} className="hover:bg-white/5 cursor-pointer">
                                                    <User className="mr-2 h-4 w-4" /> Demote to Client
                                                </DropdownMenuItem>
                                            )}
                                        </DropdownMenuContent>
                                    </DropdownMenu>
                                </TableCell>
                            </TableRow>
                        ))}
                    </TableBody>
                </Table>
            </div>

            <Dialog open={isBalanceOpen} onOpenChange={setIsBalanceOpen}>
                <DialogContent className="bg-zinc-950 border-white/10 text-white">
                    <DialogHeader>
                        <DialogTitle>Manage Balance</DialogTitle>
                        <DialogDescription>
                            Manually credit or debit {selectedUser?.name}'s account.
                        </DialogDescription>
                    </DialogHeader>
                    <div className="grid gap-4 py-4">
                        <div className="grid gap-2">
                            <Label>Action Type</Label>
                            <Select value={type} onValueChange={setType}>
                                <SelectTrigger className="bg-zinc-900 border-white/10 text-white">
                                    <SelectValue />
                                </SelectTrigger>
                                <SelectContent className="bg-zinc-900 border-white/10 text-white">
                                    <SelectItem value="CREDIT">Credit (+)</SelectItem>
                                    <SelectItem value="DEBIT">Debit (-)</SelectItem>
                                </SelectContent>
                            </Select>
                        </div>
                        <div className="grid gap-2">
                            <Label>Amount (R$)</Label>
                            <Input
                                type="number"
                                value={amount}
                                onChange={(e) => setAmount(e.target.value)}
                                className="bg-zinc-900 border-white/10 text-white"
                                placeholder="0.00"
                            />
                        </div>
                        <div className="grid gap-2">
                            <Label>Description</Label>
                            <Input
                                value={description}
                                onChange={(e) => setDescription(e.target.value)}
                                className="bg-zinc-900 border-white/10 text-white"
                                placeholder="Reason for adjustment"
                            />
                        </div>
                    </div>
                    <DialogFooter>
                        <Button variant="outline" onClick={() => setIsBalanceOpen(false)} className="border-white/10 text-white hover:bg-white/10">Cancel</Button>
                        <Button onClick={handleBalanceUpdate} className="bg-white text-black hover:bg-white/90">Confirm Update</Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </div>
    )
}

