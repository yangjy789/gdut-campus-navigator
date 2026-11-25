import axios from 'axios'
export interface PublicPlace {
 id:string; name:string; region:string; category:string; aliases:string[]; planned:boolean; description?:string;
 image_position:{x:number;y:number}; source_url:string; source_document_url:string; checked_on:string
}
export interface NavigationPlan {status:'navigation_ready';start:PublicPlace;end:PublicPlace;navigation_url:string;provider:string;distance_m:null;message:string}
export const planNavigation=(start_id:string,end_id:string)=>axios.post<NavigationPlan>('/api/campus/real/route',{start_id,end_id}).then(r=>r.data)
