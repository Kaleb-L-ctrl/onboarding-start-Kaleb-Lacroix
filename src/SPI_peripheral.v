/*
 * Copyright (c) 2025 Kaleb Lacroix
 * SPDX-License-Identifier: Apache-2.0
 */

`default_nettype none

module SPI_peripheral (
    input wire SCLK,
    input wire nCS,
    input wire COPI,
    input wire clk,
    input wire rst_n,

    output reg [7:0] en_reg_out_7_0,
    output reg [7:0] en_reg_out_15_8,
    output reg [7:0] en_reg_pwm_7_0,
    output reg [7:0] en_reg_pwm_15_8,
    output reg [7:0] pwm_duty_cycle
);



    wire SCLKRISE;
    wire nCSrise;
    reg prev_sclk;
    
    reg [1:0] SCLK_sync;
    reg [1:0] ncs_sync;
    reg [1:0] copi_sync;
   
   reg message_ready;
    reg [4:0] counter;
    reg [6:0] Madd; //message destination adress
    reg[7:0] Mdata; //message data 
    reg [15:0] copi_message;
    

    assign SCLKRISE = (SCLK_sync == 2'b01);
    assign nCSrise =  (ncs_sync == 2'b01);

    always @(posedge clk or negedge rst_n) begin//on internal clock we sample through our buffers
        if (!rst_n)begin //reset (active low)
            SCLK_sync       <= 2'b00;
            copi_sync       <= 2'b00;
            ncs_sync        <= 2'b00;
            prev_sclk       <= 0;

            en_reg_out_7_0  <= 8'b0;
            en_reg_out_15_8 <= 8'b0;
            en_reg_pwm_7_0  <= 8'b0;
            en_reg_pwm_15_8 <= 8'b0;
            pwm_duty_cycle  <= 8'b0;

            counter         <= 0;
            copi_message    <= 16'b0;
            Madd            <= 8'b0;
            Mdata           <= 8'b0;
            message_ready   <=0;

        end else begin//not reset; we capture values from contrtoler
            SCLK_sync <= {SCLK_sync[0], SCLK};
            prev_sclk <= SCLK_sync[1];
            copi_sync <= {copi_sync[0], COPI};
            ncs_sync  <= {ncs_sync[0], nCS};

        
            if (ncs_sync == 2'b10)begin
                counter <= 5'b0;
                copi_message <= 16'b0;
            end
            
            else if(SCLKRISE && ncs_sync == 2'b00) begin//data valid take a sample and run code, (SCKRISE will always be 0 on rst)
                if (counter != 5'b10000)begin
                    copi_message <= {copi_message[14:0], copi_sync[1]};//load in the new bit.
                    counter <= counter + 1;
                end
                else if (counter == 5'b10000) begin
                    counter <= 0;
                    message_ready <= 1'b1;
                end
            end
        



            if (message_ready==1'b1) begin///we ignore read
                message_ready <=0;
                if (copi_message[15]== 1'b1)begin
                    Madd  <= copi_message[14:8];
                    Mdata <= copi_message[7:0];
                    
                    case (Madd)//log all of the data to the registers when nCS is rising edge
                        7'h00:en_reg_out_7_0  <= Mdata;
                        7'h01:en_reg_out_15_8 <= Mdata;
                        7'h02:en_reg_pwm_7_0  <= Mdata;
                        7'h03:en_reg_pwm_15_8 <= Mdata;
                        7'h04:pwm_duty_cycle  <= Mdata;
                        default: ;//do nothing we are ignoring invalid adresses
                    endcase
                end
            end
        end
    end

   


    
  // All output pins must be assigned. If not used, assign to 0.

  // List all unused inputs to prevent warnings
  //wire _unused = &{ena, clk, rst_n, 1'b0};

endmodule